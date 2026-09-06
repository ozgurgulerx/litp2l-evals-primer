"""Executed lexical retrieval interventions and mock refunds, not model evaluation."""

import argparse
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import re

from cx_eval_lab.evidence import canonical_hash

ARMS = ('retrieval', 'oracle', 'full-context')
AGENTS = ('policy-control', 'wrong-amount-mutant')


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('bounded opaque identifier required')


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('bounded integer required')


@dataclass(frozen=True)
class PolicyDocument:
    document_id: str
    policy_version: str
    text: str
    refund_window_days: int

    def __post_init__(self):
        _identifier(self.document_id)
        _identifier(self.policy_version)
        _integer(self.refund_window_days, 0, 3650)
        if not isinstance(self.text, str) or not 1 <= len(self.text.strip()) <= 10_000:
            raise ValueError('bounded nonempty document text required')


@dataclass(frozen=True)
class KnowledgeCase:
    case_id: str
    query: str
    age_days: int
    amount_cents: int = 4000
    currency: str = 'USD'
    customer_id: str = 'customer-1'
    order_id: str = 'order-1'
    active_policy_version: str = 'policy-v2'

    def __post_init__(self):
        for value in (self.case_id, self.customer_id, self.order_id, self.active_policy_version):
            _identifier(value)
        _integer(self.age_days, 0, 3650)
        _integer(self.amount_cents, 1, 1_000_000)
        if self.currency not in ('USD', 'EUR'):
            raise ValueError('unsupported currency')
        if not isinstance(self.query, str) or not 1 <= len(self.query.strip()) <= 1000:
            raise ValueError('bounded nonempty customer query required')


def example_documents():
    return (PolicyDocument('doc-a', 'policy-v1',
                'Refund blue backpack orders within 90 days.', 90),
            PolicyDocument('doc-b', 'policy-v2',
                'Reimbursements for luggage purchases within 30 days.', 30))


def example_cases():
    return (KnowledgeCase('case-01', 'Refund blue backpack.', 10),
            KnowledgeCase('case-02', 'Refund blue backpack after 45 days.', 45),
            KnowledgeCase('case-03', 'Reimbursements for luggage purchases.', 10))


def _corpus(case, documents):
    if not isinstance(case, KnowledgeCase) or not 1 <= len(documents) <= 100:
        raise ValueError('case and bounded document corpus required')
    documents = tuple(PolicyDocument(**asdict(document)) for document in documents)
    if len({doc.document_id for doc in documents}) != len(documents):
        raise ValueError('duplicate document identity')
    current = tuple(doc for doc in documents if doc.policy_version == case.active_policy_version)
    if len(current) != 1:
        raise ValueError('exactly one authoritative active policy required')
    return documents, current[0]


def rank_documents(query, documents):
    """Real lexical overlap: unique lowercase alphanumeric tokens, no stemming."""
    tokens = set(re.findall(r'[a-z0-9]+', query.lower()))
    rows = [{'document_id': doc.document_id,
             'matched_terms': sorted(tokens & set(re.findall(r'[a-z0-9]+', doc.text.lower())))}
            for doc in documents]
    return sorted(({**row, 'score': len(row['matched_terms'])} for row in rows),
                  key=lambda row: (-row['score'], row['document_id']))


@dataclass(frozen=True)
class RefundEffect:
    customer_id: str
    order_id: str
    amount_cents: int
    currency: str


def _expected_arguments(case):
    return {key: getattr(case, key) for key in ('customer_id', 'order_id', 'amount_cents', 'currency')}


@dataclass(frozen=True)
class RefundLedger:
    """Fresh immutable mock state; server permission checks are outside the agent."""
    case: KnowledgeCase
    active_window_days: int
    refunds: tuple[RefundEffect, ...] = ()

    def issue_refund(self, arguments):
        args = json.loads(json.dumps(arguments, allow_nan=False))
        valid = (isinstance(args, dict) and args == _expected_arguments(self.case)
                 and type(args.get('amount_cents')) is int)
        reason = ('arguments_mismatch' if not valid else
                  'policy_denied' if self.case.age_days > self.active_window_days else
                  'duplicate_denied' if self.refunds else None)
        result = {'status': 'blocked', 'reason': reason} if reason else {'status': 'accepted'}
        updated = self if reason else replace(self, refunds=(*self.refunds, RefundEffect(**args)))
        return updated, {'tool': 'issue_refund', 'arguments': args, 'result': result}


def _decide(agent_input):
    request = agent_input['request']
    current = [doc for doc in agent_input['documents']
               if doc['policy_version'] == request['active_policy_version']]
    if len(current) != 1:
        return {'action': 'abstain', 'selected_document_id': None, 'reason': 'active_policy_unavailable'}
    doc = current[0]
    action = 'refund' if request['age_days'] <= doc['refund_window_days'] else 'deny'
    return {'action': action, 'selected_document_id': doc['document_id'], 'reason': 'structured_policy_rule'}


def _grade(case, authoritative, agent_input, decision, events, state):
    expected_action = 'refund' if case.age_days <= authoritative.refund_window_days else 'deny'
    supplied = any(doc['document_id'] == authoritative.document_id for doc in agent_input['documents'])
    arguments_correct = all(event['arguments'] == _expected_arguments(case) for event in events)
    expected_refunds = [_expected_arguments(case)] if expected_action == 'refund' else []
    decision_correct = decision['action'] == expected_action
    final_correct = state['refunds'] == expected_refunds
    return {'knowledge_in_corpus': True, 'knowledge_supplied': supplied,
            'knowledge_available': supplied,  # Compatibility alias: supplied context, not corpus coverage.
            'decision_correct': decision_correct, 'action_arguments_correct': arguments_correct,
            'final_state_correct': final_correct,
            'blocked_attempts': sum(event['result']['status'] == 'blocked' for event in events),
            'completed_denial': decision_correct and expected_action == 'deny' and not events,
            'contract_passed': supplied and decision_correct and arguments_correct and final_correct
                               and (expected_action == 'refund' or not events)}


def execute_trial(case, documents, arm, agent):
    if arm not in ARMS or agent not in AGENTS:
        raise ValueError('unknown registered arm or agent control')
    documents, authoritative = _corpus(case, documents)
    rankings = rank_documents(case.query, documents)
    context = (tuple(doc for doc in documents if doc.document_id == rankings[0]['document_id'])
               if arm == 'retrieval' else (authoritative,) if arm == 'oracle' else documents)
    agent_input = {'request': {key: value for key, value in asdict(case).items() if key != 'case_id'},
                   'documents': [asdict(doc) for doc in context]}
    decision = _decide(agent_input)
    world, events = RefundLedger(case, authoritative.refund_window_days), []
    if decision['action'] == 'refund':
        arguments = _expected_arguments(case)
        if agent == 'wrong-amount-mutant':
            arguments = {**arguments, 'amount_cents': arguments['amount_cents'] + 1}
        world, event = world.issue_refund(arguments)
        events = [event]
    state = {'refunds': [asdict(refund) for refund in world.refunds]}
    payload = {'case_id': case.case_id, 'arm': arm, 'agent': agent,
        'rankings': rankings, 'agent_input': agent_input, 'decision': decision,
        'initial_state': {'refunds': []}, 'tool_events': events, 'final_state': state,
        'grade': _grade(case, authoritative, agent_input, decision, events, state)}
    return {'payload': payload, 'artifact_hash': canonical_hash(payload)}


def _summary(trials):
    rows = []
    for agent in AGENTS:
        for arm in ARMS:
            selected = [trial['payload'] for trial in trials
                        if trial['payload']['agent'] == agent and trial['payload']['arm'] == arm]
            n = len(selected)
            count = lambda key: sum(row['grade'][key] for row in selected)
            rows.append({'agent': agent, 'arm': arm, 'case_count': n,
                'knowledge_in_corpus_count': count('knowledge_in_corpus'),
                'knowledge_supplied_count': count('knowledge_supplied'),
                'knowledge_recall': count('knowledge_supplied') / n,
                'decision_correct_count': count('decision_correct'),
                'contract_passes': count('contract_passed'), 'contract_pass_rate': count('contract_passed') / n,
                'completed_denials': count('completed_denial'), 'blocked_attempts': count('blocked_attempts')})
    return rows


def _build(cases, documents):
    if not 1 <= len(cases) <= 100 or len({case.case_id for case in cases}) != len(cases):
        raise ValueError('bounded uniquely identified case set required')
    trials = [execute_trial(case, documents, arm, agent)
              for agent in AGENTS for arm in ARMS for case in cases]
    summary = _summary(trials)
    expected = [1, 3, 3, 0, 1, 1]
    report = {'schema': 'knowledge-action-study-v1', 'evidence_kind': 'executed_deterministic_mock',
        'deployment_authorized': False,
        'inputs': {'cases': [asdict(case) for case in cases], 'documents': [asdict(doc) for doc in documents]},
        'protocol': {'arms': list(ARMS), 'agents': list(AGENTS), 'retrieval': 'unique-token-overlap-top1-id-tiebreak-v1',
                     'downstream': 'active-version-structured-window-v1'},
        'trials': trials, 'summary': summary,
        'conformance_passed': [row['contract_passes'] for row in summary] == expected,
        'limitations': 'Three scripted cases share one customer; arms and mutants are interventions, not '
            'independent population samples. Knowledge recall is current required document supplied / '
            'case count, distinct from its presence in the corpus. Decisions use structured policy '
            'fields, not language understanding or hidden reasoning. Oracle is an evaluator-controlled '
            'evidence intervention, not deployable retrieval. Full context is not matched for token '
            'budget. Wrong-amount attempts are denied by the mock server: successful boundary control '
            'does not make the agent successful. No model, human, cost, latency or deployment claims. '
            'Replay re-executes registered local controls, not authenticated historical provenance.'}
    return {**report, 'study_hash': canonical_hash(report)}


def run_study():
    return _build(example_cases(), example_documents())


def replay_study(report):
    """Re-execute retained inputs; outer rehashing cannot legitimize invented events."""
    try:
        owned = json.loads(json.dumps(report, allow_nan=False))
        if owned['study_hash'] != canonical_hash({key: value for key, value in owned.items()
                                                  if key != 'study_hash'}):
            raise ValueError('study hash mismatch')
        cases = tuple(KnowledgeCase(**value) for value in owned['inputs']['cases'])
        documents = tuple(PolicyDocument(**value) for value in owned['inputs']['documents'])
        expected = _build(cases, documents)
        if canonical_hash(owned) != canonical_hash(expected):
            raise ValueError('retained study differs from independent local re-execution')
        return tuple(expected['trials'])
    except (TypeError, KeyError, AttributeError, RecursionError) as error:
        raise ValueError('invalid retained knowledge-action study') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new knowledge-action artifact path.\n')
    report = run_study()
    replay_study(report)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if not report['conformance_passed']:
        parser.exit(1, 'Knowledge-action controls did not reproduce.\n')


if __name__ == '__main__':
    main()
