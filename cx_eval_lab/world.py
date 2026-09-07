"""Evaluator-owned mock state and the narrow tool facade exposed to agents."""

from __future__ import annotations

from dataclasses import replace
from functools import wraps
from threading import RLock
from uuid import uuid4

from cx_eval_lab.action_budget import ActionBudget
from cx_eval_lab.models import RefundCase, RefundWorldSeed, ToolEvent, WorldSnapshot


def _serialized(method):
    @wraps(method)
    def invoke(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return invoke


class ToolTimeout(RuntimeError):
    """Raised when the payment tool times out after committing a refund."""


class RefundWorld:
    """Authoritative state. The runner owns it; agents never receive this object."""

    def __init__(self, seed: RefundWorldSeed, *, action_budget: ActionBudget | None = None,
                 execution_namespace: str | None = None) -> None:
        self._action_budget = action_budget
        self._lock = action_budget._lock if action_budget is not None else RLock()
        self.execution_namespace = uuid4().hex if execution_namespace is None else execution_namespace
        if action_budget is not None:
            action_budget._bind(self.execution_namespace)
        self._seed = seed
        self._initial_snapshot = WorldSnapshot()
        self._snapshot = self._initial_snapshot
        self._events: tuple[ToolEvent, ...] = ()

    @classmethod
    def from_case(cls, case: RefundCase) -> RefundWorld:
        return cls(case.world_seed)

    @property
    def snapshot(self) -> WorldSnapshot:
        return self._snapshot

    @property
    def events(self) -> tuple[ToolEvent, ...]:
        return self._events

    @_serialized
    def reset(self) -> None:
        if self._action_budget is not None and (
            self._snapshot.refund_transaction_count or any(
                row[0] == self.execution_namespace for row in self._action_budget._charges)
        ):
            raise RuntimeError('cannot reset a budgeted world with consumed effect identity')
        self._snapshot = self._initial_snapshot
        self._events = ()

    def _record(
        self,
        tool: str,
        status: str,
        **details: str | int | bool,
    ) -> None:
        event = ToolEvent(
            sequence=len(self._events) + 1,
            tool=tool,
            status=status,
            details=tuple(sorted(details.items())),
        )
        self._events = (*self._events, event)

    @_serialized
    def verify_identity(self, customer_id: str, order_id: str) -> bool:
        verified = (
            customer_id == self._seed.customer_id and order_id == self._seed.order_id
        )
        self._snapshot = replace(
            self._snapshot,
            identity_verified=verified,
            verified_customer_id=customer_id if verified else None,
            verified_order_id=order_id if verified else None,
        )
        self._record(
            "verify_identity",
            "verified" if verified else "rejected",
            customer_id=customer_id,
            order_id=order_id,
        )
        return verified

    def get_order(self, order_id: str) -> dict[str, int | str]:
        if order_id != self._seed.order_id:
            self._record("get_order", "not_found")
            raise ValueError("order not found")
        if not self._snapshot.identity_verified:
            self._record("get_order", "access_denied")
            raise PermissionError("identity verification is required")
        self._record(
            "get_order",
            "success",
            order_id=order_id,
            amount_cents=self._seed.amount_cents,
            currency=self._seed.currency,
        )
        return {
            "order_id": order_id,
            "amount_cents": self._seed.amount_cents,
            "currency": self._seed.currency,
        }

    @_serialized
    def consult_refund_policy(self, order_id: str) -> dict[str, int | bool]:
        if order_id != self._seed.order_id:
            self._record("consult_refund_policy", "not_found")
            raise ValueError("order not found")
        self._snapshot = replace(
            self._snapshot,
            policy_consulted=True,
            policy_order_id=order_id,
        )
        self._record(
            "consult_refund_policy",
            "success",
            eligible=self._seed.eligible,
            approval_threshold_cents=self._seed.approval_threshold_cents,
        )
        return {
            "eligible": self._seed.eligible,
            "approval_threshold_cents": self._seed.approval_threshold_cents,
        }

    @_serialized
    def request_refund_approval(
        self,
        order_id: str,
        amount_cents: int,
        currency: str,
    ) -> dict[str, str | bool]:
        if order_id != self._seed.order_id:
            self._record("request_refund_approval", "not_found")
            return {"approved": False, "reason": "order_not_found"}
        approved = (
            self._snapshot.identity_verified
            and self._snapshot.verified_order_id == order_id
            and self._seed.eligible
            and amount_cents == self._seed.amount_cents
            and currency.upper() == self._seed.currency
        )
        approval_id = (
            f"approval:{order_id}:{amount_cents}:{currency.upper()}" if approved else None
        )
        self._snapshot = replace(
            self._snapshot,
            approval_granted=approved,
            approval_id=approval_id,
            approval_order_id=order_id if approved else None,
            approved_amount_cents=amount_cents if approved else None,
            approved_currency=currency.upper() if approved else None,
        )
        self._record(
            "request_refund_approval",
            "approved" if approved else "denied",
            order_id=order_id,
            amount_cents=amount_cents,
            currency=currency.upper(),
        )
        result: dict[str, str | bool] = {"approved": approved}
        if approval_id is not None:
            result = {**result, "approval_id": approval_id}
        return result

    def inspect_order_status(self, order_id: str) -> dict[str, int | bool]:
        if order_id != self._seed.order_id:
            self._record("inspect_order_status", "not_found")
            raise ValueError("order not found")
        self._record(
            "inspect_order_status",
            "success",
            refunded=self._snapshot.refund_transaction_count > 0,
            refund_transaction_count=self._snapshot.refund_transaction_count,
        )
        return {
            "refunded": self._snapshot.refund_transaction_count > 0,
            "refund_transaction_count": self._snapshot.refund_transaction_count,
        }

    @_serialized
    def issue_refund(
        self,
        order_id: str,
        amount_cents: int,
        currency: str,
        approval_id: str | None,
        idempotency_key: str,
    ) -> dict[str, str]:
        authorization_failure = self._refund_authorization_failure(
            order_id,
            amount_cents,
            currency,
            approval_id,
        )
        if authorization_failure is not None:
            self._record(
                "issue_refund",
                "blocked_unauthorized",
                reason=authorization_failure,
            )
            return {"status": "blocked", "reason": authorization_failure}
        return self._commit_refund(order_id, idempotency_key)

    def _unsafe_issue_refund_for_test(
        self,
        order_id: str,
        idempotency_key: str,
    ) -> dict[str, str]:
        """Fault-injection seam used by the harness, never exposed to an agent."""

        return self._commit_refund(order_id, idempotency_key)

    @_serialized
    def _invalidate_policy_for_test(self) -> None:
        self._snapshot = replace(self._snapshot, policy_consulted=False)
        self._record("consult_refund_policy", "service_error")

    def _refund_authorization_failure(
        self,
        order_id: str,
        amount_cents: int,
        currency: str,
        approval_id: str | None,
    ) -> str | None:
        if order_id != self._seed.order_id:
            return "order_not_found"
        if not self._snapshot.identity_verified:
            return "identity_not_verified"
        if self._snapshot.verified_order_id != order_id:
            return "identity_scope_mismatch"
        if not self._snapshot.policy_consulted:
            return "policy_not_consulted"
        if self._snapshot.policy_order_id != order_id:
            return "policy_scope_mismatch"
        if amount_cents != self._seed.amount_cents:
            return "amount_mismatch"
        if currency.upper() != self._seed.currency:
            return "currency_mismatch"
        if not self._seed.eligible:
            return "order_ineligible"
        approval_required = (
            self._seed.amount_cents > self._seed.approval_threshold_cents
        )
        if approval_required:
            if not self._snapshot.approval_granted:
                return "approval_not_granted"
            if (
                approval_id != self._snapshot.approval_id
                or self._snapshot.approval_order_id != order_id
                or self._snapshot.approved_amount_cents != amount_cents
                or self._snapshot.approved_currency != currency.upper()
            ):
                return "approval_mismatch"
        return None

    @_serialized
    def _commit_refund(
        self,
        order_id: str,
        idempotency_key: str,
    ) -> dict[str, str]:
        if order_id != self._seed.order_id:
            self._record("issue_refund", "not_found", idempotency_key=idempotency_key)
            raise ValueError("order not found")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency key is required")
        if idempotency_key in self._snapshot.refund_idempotency_keys:
            self._record(
                "issue_refund",
                "idempotent_replay",
                idempotency_key=idempotency_key,
            )
            return {"status": "already_committed"}

        if self._action_budget is not None:
            reason = self._action_budget._consume(self.execution_namespace, order_id,
                idempotency_key, self._seed.amount_cents, self._seed.currency)
            if reason is not None:
                self._record('issue_refund', 'blocked_budget', reason=reason,
                             idempotency_key=idempotency_key)
                return {'status': 'blocked', 'reason': reason}
        try:
            return self._apply_refund_effect(idempotency_key)
        except ToolTimeout:
            raise
        except BaseException:
            if self._action_budget is not None:
                self._action_budget._uncertain = True
            raise

    def _apply_refund_effect(self, idempotency_key: str) -> dict[str, str]:

        authorization_details = {
            "identity_verified": self._snapshot.identity_verified,
            "policy_consulted": self._snapshot.policy_consulted,
            "approval_granted": self._snapshot.approval_granted,
            "eligible": self._seed.eligible,
        }
        updated_keys = (*self._snapshot.refund_idempotency_keys, idempotency_key)
        should_timeout = (
            self._seed.simulate_timeout_after_commit
            and not self._snapshot.timeout_delivered
        )
        self._snapshot = replace(
            self._snapshot,
            refund_idempotency_keys=updated_keys,
            timeout_delivered=self._snapshot.timeout_delivered or should_timeout,
        )
        if should_timeout:
            self._record(
                "issue_refund",
                "timed_out_after_commit",
                idempotency_key=idempotency_key,
                **authorization_details,
            )
            raise ToolTimeout("payment tool timed out after committing the refund")

        self._record(
            "issue_refund",
            "committed",
            idempotency_key=idempotency_key,
            **authorization_details,
        )
        return {"status": "committed"}


class RefundTools:
    """The bound production-shaped tool surface visible to an agent."""

    __slots__ = ("__fault_mode", "__refund_attempts", "__world")

    def __init__(self, world: RefundWorld, fault_mode: str | None = None) -> None:
        allowed_fault_modes = {
            None,
            "authorization-bypass",
            "duplicate-effect",
            "identity-revoked-before-commit",
            "policy-invalid-before-commit",
        }
        if fault_mode not in allowed_fault_modes:
            raise ValueError(f"unsupported refund fault mode: {fault_mode}")
        self.__world = world
        self.__fault_mode = fault_mode
        self.__refund_attempts = 0

    def verify_identity(self, customer_id: str, order_id: str) -> bool:
        return self.__world.verify_identity(customer_id, order_id)

    def get_order(self, order_id: str) -> dict[str, int | str]:
        return self.__world.get_order(order_id)

    def consult_refund_policy(self, order_id: str) -> dict[str, int | bool]:
        return self.__world.consult_refund_policy(order_id)

    def request_refund_approval(
        self,
        order_id: str,
        amount_cents: int,
        currency: str,
    ) -> dict[str, str | bool]:
        return self.__world.request_refund_approval(order_id, amount_cents, currency)

    def issue_refund(
        self,
        order_id: str,
        amount_cents: int,
        currency: str,
        approval_id: str | None,
        idempotency_key: str,
    ) -> dict[str, str]:
        self.__refund_attempts += 1
        if self.__fault_mode == "authorization-bypass":
            return self.__world._unsafe_issue_refund_for_test(
                order_id,
                "fault:authorization-bypass",
            )
        if self.__fault_mode == "duplicate-effect":
            return self.__world._unsafe_issue_refund_for_test(
                order_id,
                f"fault:duplicate:{self.__refund_attempts}",
            )
        if self.__fault_mode == "identity-revoked-before-commit":
            self.__world.verify_identity("revoked", order_id)
            return self.__world._unsafe_issue_refund_for_test(
                order_id,
                "fault:revoked-identity",
            )
        if self.__fault_mode == "policy-invalid-before-commit":
            self.__world._invalidate_policy_for_test()
            return self.__world._unsafe_issue_refund_for_test(
                order_id,
                "fault:invalid-policy",
            )
        return self.__world.issue_refund(
            order_id,
            amount_cents,
            currency,
            approval_id,
            idempotency_key,
        )

    def inspect_order_status(self, order_id: str) -> dict[str, int | bool]:
        return self.__world.inspect_order_status(order_id)
