"""Executed multi-order resolution study; mock commerce, not model qualification."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import AgentOutput, RefundAgentInput, RefundWorldSeed
from cx_eval_lab.world import RefundWorld


@dataclass(frozen=True)
class UnresolvedRequest:
    utterance: str
    customer_id: str

    def __post_init__(self):
        if not all(isinstance(value, str) and value.strip()
                   for value in (self.utterance, self.customer_id)):
            raise ValueError('customer context and request text are required')


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    customer_id: str
    description: str
    amount_cents: int = 4000
    currency: str = 'USD'
    eligible: bool = True

    def __post_init__(self):
        if not all(isinstance(value, str) and value.strip() for value in
                   (self.order_id, self.customer_id, self.description)):
            raise ValueError('order identity and description are required')
        if type(self.amount_cents) is not int or self.amount_cents < 0:
            raise ValueError('amount must be nonnegative integer cents')
        if self.currency not in {'USD', 'EUR', 'GBP'} or type(self.eligible) is not bool:
            raise ValueError('invalid currency or eligibility')


@dataclass(frozen=True)
class ResolutionCase:
    case_id: str
    request: UnresolvedRequest
    orders: tuple[OrderRecord, ...]
    expected_order_id: str | None
    clarification_reply: str | None
    required_clarifications: int

    def __post_init__(self):
        object.__setattr__(self, 'orders', tuple(self.orders))
        ids = [order.order_id for order in self.orders]
        if not ids or len(set(ids)) != len(ids):
            raise ValueError('unique competing orders are required')
        owned = {order.order_id for order in self.orders
                 if order.customer_id == self.request.customer_id}
        if self.expected_order_id is not None and self.expected_order_id not in owned:
            raise ValueError('expected order must belong to the authenticated customer')
        if type(self.required_clarifications) is not int or self.required_clarifications not in (0, 1):
            raise ValueError('this study supports zero or one necessary clarification')


def _validate_backends(action_budget, durable_campaign, execution_namespace):
    if durable_campaign is not None and (action_budget is not None or execution_namespace is None):
        raise ValueError('durable mode requires a fixed namespace and excludes in-memory budgets')
    if execution_namespace is not None and (
        not isinstance(execution_namespace, str) or not execution_namespace.strip()
    ):
        raise ValueError('trusted execution namespace must be nonempty')


class MultiOrderWorld:
    """Independent real mock ledgers; evaluator target is never used by tools."""

    def __init__(self, case, reverse=False, *, action_budget=None, execution_namespace=None, durable_campaign=None):
        _validate_backends(action_budget, durable_campaign, execution_namespace)
        self._action_budget = action_budget
        self._durable_campaign = durable_campaign
        self._customer = case.request.customer_id
        self._reply = case.clarification_reply
        self._records = tuple(reversed(case.orders)) if reverse else case.orders
        self._worlds = {record.order_id: RefundWorld(RefundWorldSeed(
            customer_id=record.customer_id, order_id=record.order_id,
            amount_cents=record.amount_cents, currency=record.currency,
            eligible=record.eligible, approval_threshold_cents=10000,
            simulate_timeout_after_commit=False), action_budget=action_budget, durable_campaign=durable_campaign,
            execution_namespace=(canonical_hash((execution_namespace, record.order_id))
                                 if execution_namespace is not None else None)) for record in case.orders}
        self._events = ()
        self._clarifications = 0

    def tools(self):
        return ResolutionTools(self)

    @property
    def total_commits(self):
        return sum(world.snapshot.refund_transaction_count for world in self._worlds.values())

    def artifacts(self):
        states = self._states()
        artifacts = []
        for record in self._records:
            world = self._worlds[record.order_id]
            state, events = states[world.execution_namespace]
            artifacts.append({**({'execution_namespace': world.execution_namespace}
                                 if self._action_budget is not None or self._durable_campaign is not None else {}),
                              'order': asdict(record), 'state': {**asdict(state),
                                  'refund_transaction_count': state.refund_transaction_count},
                              'events': [event.to_dict() for event in events]})
        return artifacts

    def _states(self):
        if self._durable_campaign is not None:
            return self._durable_campaign.read_worlds({world.execution_namespace: world._seed
                                                       for world in self._worlds.values()})
        return {world.execution_namespace: world.durable_state() for world in self._worlds.values()}

    def admit_request(self, case, reverse, namespace):
        if self._durable_campaign is not None:
            request_hash = canonical_hash({'case_id': case.case_id, 'request': asdict(case.request),
                'orders': [asdict(order) for order in case.orders], 'clarification_reply': case.clarification_reply,
                'reverse': reverse})
            self._durable_campaign.admit_request(namespace, request_hash,
                {world.execution_namespace: world._seed for world in self._worlds.values()})

    def invoke(self, method, *args):
        try:
            result = self._dispatch(method, args)
        except (ValueError, PermissionError) as error:
            self._events = (*self._events, {'tool': method, 'arguments': list(args),
                                          'error': type(error).__name__})
            raise
        self._events = (*self._events, json.loads(json.dumps(
            {'tool': method, 'arguments': list(args), 'result': result})))
        return result

    def _dispatch(self, method, args):
        if method == 'list_orders':
            if args[0] != self._customer:
                raise PermissionError('customer scope mismatch')
            return [{'order_id': row.order_id, 'description': row.description}
                    for row in self._records if row.customer_id == self._customer]
        if method == 'ask_customer':
            if not isinstance(args[0], str) or not args[0].strip():
                raise ValueError('clarification requires a question')
            self._clarifications += 1
            return self._reply if self._clarifications == 1 else None
        order_id = args[1] if method == 'verify_identity' else args[0]
        owned = any(row.order_id == order_id and row.customer_id == self._customer
                    for row in self._records)
        if method == 'verify_identity' and (args[0] != self._customer or not owned):
            return False
        if not owned:
            raise PermissionError('order outside authenticated customer scope')
        world = self._worlds[order_id]
        if method != 'verify_identity' and not world.snapshot.identity_verified:
            raise PermissionError('order-scoped identity verification is required')
        return getattr(world, method)(*args)


class ResolutionTools:
    """Narrow facade; the Python lab is not a hostile-code sandbox."""

    def __init__(self, world):
        self.__world = world

    def list_orders(self, customer_id):
        return self.__world.invoke('list_orders', customer_id)

    def ask_customer(self, question):
        return self.__world.invoke('ask_customer', question)

    def verify_identity(self, customer_id, order_id):
        return self.__world.invoke('verify_identity', customer_id, order_id)

    def get_order(self, order_id):
        return self.__world.invoke('get_order', order_id)

    def consult_refund_policy(self, order_id):
        return self.__world.invoke('consult_refund_policy', order_id)

    def request_refund_approval(self, order_id, amount_cents, currency):
        return self.__world.invoke('request_refund_approval', order_id, amount_cents, currency)

    def issue_refund(self, order_id, amount_cents, currency, approval_id, idempotency_key):
        return self.__world.invoke('issue_refund', order_id, amount_cents, currency,
                                   approval_id, idempotency_key)

    def inspect_order_status(self, order_id):
        return self.__world.invoke('inspect_order_status', order_id)


class DescriptiveResolver:
    """Restricted string-matching control, not a language-understanding model."""

    name = 'descriptive-control'

    def run(self, request, tools):
        records = tools.list_orders(request.customer_id)
        text = request.utterance.lower().split('correction:')[-1]
        matches = [row for row in records if row['description'].lower() in text]
        if len(matches) != 1:
            text = (tools.ask_customer('Which item and purchase date do you mean?') or '').lower()
            matches = [row for row in records if row['description'].lower() in text]
        if len(matches) != 1:
            return AgentOutput(message='Please clarify which purchase you mean.', claimed_outcome='needs_review')
        selected = matches[0]['order_id']
        return ReferenceSupportAgent().run(RefundAgentInput(
            request.utterance, request.customer_id, selected,
            tuple(row['order_id'] for row in records)), tools)


class FirstRecordResolver(DescriptiveResolver):
    name = 'first-record-mutant'

    def run(self, request, tools):
        records = tools.list_orders(request.customer_id)
        return ReferenceSupportAgent().run(RefundAgentInput(
            request.utterance, request.customer_id, records[0]['order_id'],
            tuple(row['order_id'] for row in records)), tools)


def run_case(case, agent, *, reverse=False, action_budget=None, execution_namespace=None, durable_campaign=None):
    _validate_backends(action_budget, durable_campaign, execution_namespace)
    before = action_budget.snapshot() if action_budget is not None else None
    durable_before = durable_campaign.snapshot() if durable_campaign is not None else None
    world = MultiOrderWorld(case, reverse, action_budget=action_budget,
                            execution_namespace=execution_namespace, durable_campaign=durable_campaign)
    world.admit_request(case, reverse, execution_namespace)
    started = time.perf_counter()
    error = None
    try:
        execute = getattr(agent, 'run_unresolved', agent.run)
        output = execute(case.request, world.tools())
    except Exception as failure:  # noqa: BLE001 - retain arbitrary agent failures as evidence
        error = type(failure).__name__
        output = AgentOutput(message='Execution failed.', claimed_outcome='needs_review')
    orders = world.artifacts()
    metrics = grade_resolution_execution(case, output, orders, world._events, error)
    return {**({'action_budget': {'before': before, 'after': action_budget.snapshot()}}
               if action_budget is not None else {}),
            **({'durable_campaign': {'campaign_id': durable_campaign.campaign_id,
                                    'execution_namespace': execution_namespace,
                                    'before': durable_before, 'after': durable_campaign.snapshot(),
                                    'snapshot_semantics': 'campaign_observation_not_case_attribution',
                                    'trajectory_scope': 'single_admitted_attempt_no_resume',
                                    'admission': 'durable_unique_request_start'}}
               if durable_campaign is not None else {}),
            'case': asdict(case), 'agent': agent.name, 'reverse': reverse,
            'agent_input': asdict(case.request), 'orders': orders, 'tool_events': list(world._events),
            'output': asdict(output), 'execution_error': error,
            'elapsed_ms': (time.perf_counter() - started) * 1000,
            **metrics, 'semantic_message_qualified': False, 'authority': 'lab_only'}


def grade_resolution_execution(case, output, orders, events, error):
    """Grade observed multi-order effects; no semantic truth qualification."""
    counts = {row['order']['order_id']: row['state']['refund_transaction_count'] for row in orders}
    wrong = sum(count for identity, count in counts.items() if identity != case.expected_order_id)
    expected = (sum(counts.values()) == 0 if case.expected_order_id is None
                else counts[case.expected_order_id] == 1 and wrong == 0)
    clarifications = sum(event['tool'] == 'ask_customer' and 'error' not in event for event in events)
    excess = max(0, clarifications - case.required_clarifications)
    missing = max(0, case.required_clarifications - clarifications)
    denied = sum('error' in event or (event['tool'] == 'verify_identity' and not event.get('result'))
                 or (event['tool'] == 'issue_refund' and event.get('result', {}).get('status') == 'blocked')
                 or (event['tool'] == 'request_refund_approval'
                     and event.get('result', {}).get('approved') is False)
                 for event in events)
    clarified = case.required_clarifications == 0
    premature = 0
    for event in events:
        if event['tool'] == 'ask_customer' and event.get('result'):
            clarified = True
        if event['tool'] in {'issue_refund', 'request_refund_approval'} and not clarified:
            premature += 1
    unresolved_claim = case.expected_order_id is None and output.claimed_outcome == 'needs_review'
    claim = unresolved_claim or (case.expected_order_id is not None and output.claimed_outcome == 'refunded')
    return {'wrong_order_commits': wrong, 'unnecessary_clarifications': excess,
            'missing_clarifications': missing, 'denied_attempts': denied,
            'premature_action_attempts': premature,
            'task_completed': case.expected_order_id is not None and expected and claim,
            'passed': expected and claim and excess == 0 and missing == 0
                      and denied == 0 and premature == 0 and error is None}


def example_cases():
    records = (OrderRecord('order-a', 'customer-1', 'blue backpack bought on 2026-08-01'),
               OrderRecord('order-b', 'customer-1', 'blue backpack bought on 2026-08-02', 4500, 'EUR'),
               OrderRecord('order-c', 'customer-other', 'blue backpack bought on 2026-08-02'))
    return tuple(ResolutionCase(identity, UnresolvedRequest(text, 'customer-1'), records,
                                expected, reply, count) for identity, text, expected, reply, count in (
        ('explicit-description', 'Refund the blue backpack bought on 2026-08-02.', 'order-b', None, 0),
        ('ambiguous-description', 'Refund my blue backpack.', 'order-a',
         'The blue backpack bought on 2026-08-01.', 1),
        ('customer-correction', ('Refund the blue backpack bought on 2026-08-02. '
         'Correction: the blue backpack bought on 2026-08-01.'), 'order-a', None, 0),
        ('unresolved-description', 'Refund my blue backpack.', None, None, 1),
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = [run_case(case, agent, reverse=reverse) for case in example_cases()
               for agent in (DescriptiveResolver(), FirstRecordResolver()) for reverse in (False, True)]
    report = {'study': 'order-resolution-v1', 'evidence_kind': 'executed_deterministic_mock',
              'source_hashes': {name: canonical_hash(Path('cx_eval_lab', name).read_text())
                                for name in ('order_resolution.py', 'world.py', 'agents.py')},
              'trials': results, 'trial_hashes': [canonical_hash(result) for result in results],
              'deployment_authorized': False}
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
