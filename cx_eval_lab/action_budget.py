"""Evaluator-owned single-process mock effect allowance; no durable authority."""

from threading import RLock


class ActionBudget:
    """Shared campaign allowance, deliberately absent from the agent tool API.

    RefundWorld holds this lock across validation, accounting and its effect.
    A reservation is never released after an ambiguous failure.
    """

    def __init__(self, max_actions: int, currency_caps: dict[str, int]) -> None:
        if type(max_actions) is not int or max_actions < 0:
            raise ValueError('action cap must be a nonnegative integer')
        if not isinstance(currency_caps, dict) or any(
            currency not in {'USD', 'EUR', 'GBP'} or type(cap) is not int or cap < 0
            for currency, cap in currency_caps.items()
        ):
            raise ValueError('currency caps require registered currencies and integer cents')
        self._lock = RLock()
        self._max_actions = max_actions
        self._caps = dict(currency_caps)
        self._charges: tuple[tuple[str, str, str, int, str], ...] = ()
        self._namespaces: frozenset[str] = frozenset()
        self._denials: tuple[dict[str, str | int], ...] = ()
        self._uncertain = False

    def _bind(self, namespace: str) -> None:
        with self._lock:
            if not isinstance(namespace, str) or not namespace.strip():
                raise ValueError('execution namespace must be nonempty')
            if namespace in self._namespaces:
                raise ValueError('execution namespace already bound to an authoritative world')
            self._namespaces = self._namespaces | {namespace}

    def _consume(self, namespace: str, order: str, key: str, amount: int, currency: str) -> str | None:
        """Called only with the shared world/effect lock held, after local replay."""
        reason = None
        if self._uncertain:
            reason = 'budget_uncertain'
        elif currency not in self._caps:
            reason = 'budget_currency_unregistered'
        elif type(amount) is not int or amount < 0:
            reason = 'budget_invalid_amount'
        elif any(row[:3] == (namespace, order, key) for row in self._charges):
            reason = 'budget_missing_effect_evidence'
        elif len(self._charges) >= self._max_actions:
            reason = 'budget_action_limit'
        elif sum(row[3] for row in self._charges if row[4] == currency) + amount > self._caps[currency]:
            reason = 'budget_currency_limit'
        if reason is not None:
            self._denials = (*self._denials, {'execution_namespace': namespace,
                'order_id': order, 'idempotency_key': key, 'amount_cents': amount,
                'currency': currency, 'reason': reason})
            return reason
        self._charges = (*self._charges, (namespace, order, key, amount, currency))
        return None

    def snapshot(self) -> dict:
        with self._lock:
            spent = {currency: sum(row[3] for row in self._charges if row[4] == currency)
                     for currency in self._caps}
            return {'max_actions': self._max_actions, 'currency_caps': dict(self._caps),
                    'charged_actions': len(self._charges),
                    'remaining_actions': self._max_actions - len(self._charges),
                    'charged_cents': spent,
                    'remaining_cents': {key: cap - spent[key] for key, cap in self._caps.items()},
                    'uncertain': self._uncertain,
                    'denials': [dict(row) for row in self._denials],
                    'charges': [{'execution_namespace': row[0], 'order_id': row[1],
                                 'idempotency_key': row[2], 'amount_cents': row[3], 'currency': row[4]}
                                for row in self._charges],
                    'authority': 'single_process_mock_only', 'deployment_authorized': False}
