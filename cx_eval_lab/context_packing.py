"""Executed multi-evidence retrieval/packing controls; UTF-8 bytes are not model tokens."""

import argparse
import json
import re
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash

ARMS = ('top2', 'top5', 'filtered-top5', 'oracle')
AGENTS = ('policy-control', 'ignore-limit-mutant')
UNITS = ('window_days', 'max_refund_cents')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _fields(value, keys):
    _require(isinstance(value, dict) and set(value) == set(keys), 'exact registered fields required')


def _int(value, low=0, high=1_000_000):
    value_type = type(value)
    _require(value_type is int and low <= value <= high, 'bounded exact integer required')


def _id(value):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value), 'opaque identifier required')


def example_inputs():
    window = {'text': 'refund policy eligibility order', 'facts': {'window_days': 30}}
    contents = (window, json.loads(_json(window)),
        {'text': 'refund policy limit', 'facts': {'max_refund_cents': 5000}},
        {'text': 'refund policy', 'facts': {'window_days': 90, 'max_refund_cents': 10000}},
        {'text': 'refund ' + 'ü' * 80, 'facts': {}})
    return {'query': 'refund policy eligibility order limit', 'budget_bytes': 240,
        'policy': {'version': 'policy-v2', 'window_days': 30, 'max_refund_cents': 5000},
        'passages': [{'passage_id': name, 'version': 'policy-v1' if i == 3 else 'policy-v2',
            'source_kind': 'promotion' if i == 4 else 'authoritative-policy', 'updated_at': i + 1,
            'content': content} for i, (name, content) in enumerate(zip(
                ('window', 'window-copy', 'limit', 'stale', 'promo'), contents, strict=True))],
        'cases': [{'case_id': name, 'customer_id': f'customer-{i}', 'order_id': f'order-{i}',
            'currency': 'USD', 'age_days': age, 'amount_cents': amount}
            for i, (name, age, amount) in enumerate((('eligible', 10, 4000),
                ('too-old', 45, 4000), ('over-limit', 10, 6000)))]}


def _content(content):
    _fields(content, ('text', 'facts'))
    _require(isinstance(content['text'], str) and 0 < len(content['text'].encode('utf-8')) <= 10000,
             'bounded nonempty passage text required')
    facts = content['facts']
    _require(isinstance(facts, dict) and set(facts).issubset(UNITS), 'unknown policy fact')
    for value in facts.values():
        _int(value)


def _validate(inputs):
    _fields(inputs, ('query', 'budget_bytes', 'policy', 'passages', 'cases'))
    _int(inputs['budget_bytes'], 2, 100000)
    _require(isinstance(inputs['query'], str) and 0 < len(inputs['query']) <= 1000, 'bounded query required')
    policy = inputs['policy']
    _fields(policy, ('version', *UNITS))
    _id(policy['version'])
    for unit in UNITS:
        _int(policy[unit], 1)
    passages = inputs['passages']
    _require(isinstance(passages, list) and 1 <= len(passages) <= 100, 'bounded corpus required')
    for passage in passages:
        _fields(passage, ('passage_id', 'version', 'source_kind', 'updated_at', 'content'))
        _id(passage['passage_id'])
        _id(passage['version'])
        _int(passage['updated_at'])
        _require(passage['source_kind'] in {'authoritative-policy', 'promotion'}, 'unsupported source kind')
        _content(passage['content'])
    _require(len({p['passage_id'] for p in passages}) == len(passages), 'duplicate passage ID')
    current = [p for p in passages if p['version'] == policy['version'] and p['source_kind'] == 'authoritative-policy']
    for unit in UNITS:
        values = {p['content']['facts'][unit] for p in current if unit in p['content']['facts']}
        _require(values == {policy[unit]}, 'incomplete or contradictory authoritative current policy corpus')
    cases = inputs['cases']
    _require(isinstance(cases, list) and 1 <= len(cases) <= 20, 'bounded case set required')
    for case in cases:
        _fields(case, ('case_id', 'customer_id', 'order_id', 'currency', 'age_days', 'amount_cents'))
        for key in ('case_id', 'customer_id', 'order_id'):
            _id(case[key])
        _require(case['currency'] in {'USD', 'EUR'}, 'unsupported currency')
        _int(case['age_days'])
        _int(case['amount_cents'], 1)
    _require(len({c['case_id'] for c in cases}) == len(cases), 'duplicate case ID')


def rank_passages(query, passages):
    tokens = set(re.findall(r'[a-z0-9]+', query.lower()))
    rows = [{'passage_id': p['passage_id'], 'matched_terms': sorted(
        tokens & set(re.findall(r'[a-z0-9]+', p['content']['text'].lower())))} for p in passages]
    return sorted(({**row, 'score': len(row['matched_terms'])} for row in rows),
                  key=lambda row: (-row['score'], row['passage_id']))


def evidence_units(passages, policy):
    """Evaluator-only coverage: duplicate current sources are alternate support for one unit."""
    return [unit for unit in UNITS if any(p['version'] == policy['version']
        and p['source_kind'] == 'authoritative-policy' and p['content']['facts'].get(unit) == policy[unit]
        for p in passages)]


def _select(ranked, passages, policy, arm):
    lookup = {p['passage_id']: p for p in passages}
    retrieved = [lookup[row['passage_id']] for row in ranked[:2 if arm == 'top2' else 5]]
    if arm == 'oracle':
        # Gold diagnostic arm only; never shared with the metadata repair filter.
        retrieved = []
        for unit in UNITS:
            found = next(p for p in passages if unit in evidence_units([p], policy))
            if found not in retrieved:
                retrieved = [*retrieved, found]
    selected, events, seen = [], [], set()
    for p in retrieved:
        digest = canonical_hash(p['content'])
        reason = ('drop_version' if p['version'] != policy['version'] else
                  'drop_source_kind' if p['source_kind'] != 'authoritative-policy' else
                  'drop_duplicate' if digest in seen else 'keep') if arm == 'filtered-top5' else 'keep'
        events = [*events, {'passage_id': p['passage_id'], 'decision': reason, 'content_hash': digest}]
        if reason == 'keep':
            selected = [*selected, p]
            seen = seen | {digest}
    return retrieved, selected, events


def pack_passages(passages, budget_bytes, *, recency_first=True):
    """Whole JSON passage objects, including fact fields/punctuation, fit or are dropped."""
    _int(budget_bytes, 2, 100000)
    ordered = sorted(passages, key=lambda p: (-p['updated_at'], p['passage_id'])) if recency_first else list(passages)
    packed, events = [], []
    for passage in ordered:
        proposed = _json([p['content'] for p in (*packed, passage)])
        fits = len(proposed.encode('utf-8')) <= budget_bytes
        events = [*events, {'passage_id': passage['passage_id'], 'proposed_body_bytes': len(proposed.encode('utf-8')),
                            'decision': 'pack' if fits else 'drop_budget'}]
        packed = [*packed, passage] if fits else packed
    return packed, _json([p['content'] for p in packed]), events


def decide(agent_input, agent):
    _require(agent in AGENTS, 'unknown control')
    _fields(agent_input, ('request', 'context_body'))
    context = json.loads(agent_input['context_body'])
    _require(isinstance(context, list), 'context must be a JSON array')
    for passage in context:
        _content(passage)
    values = {unit: {p['facts'][unit] for p in context if unit in p['facts']} for unit in UNITS}
    if any(len(items) != 1 for items in values.values()):
        return {'action': 'abstain', 'reason': 'incomplete_or_conflicting_policy_bundle'}
    facts = {unit: next(iter(items)) for unit, items in values.items()}
    request = agent_input['request']
    _int(request['age_days'])
    _int(request['amount_cents'], 1)
    allowed = request['age_days'] <= facts['window_days'] and (
        agent == 'ignore-limit-mutant' or request['amount_cents'] <= facts['max_refund_cents'])
    return {'action': 'refund' if allowed else 'deny', 'reason': 'restricted_structured_policy_interpreter'}


def _backend(case, decision, policy):
    arguments = {k: case[k] for k in ('customer_id', 'order_id', 'currency', 'amount_cents')}
    if decision['action'] != 'refund':
        return [], {'refunds': []}
    reason = ('age_window' if case['age_days'] > policy['window_days'] else
              'amount_limit' if case['amount_cents'] > policy['max_refund_cents'] else None)
    result = {'status': 'blocked', 'reason': reason} if reason else {'status': 'committed'}
    return [{'tool': 'issue_refund', 'arguments': arguments, 'result': result}], {'refunds': [] if reason else [arguments]}


def _trial(inputs, case, arm, agent, registration_hash):
    passages, policy = inputs['passages'], inputs['policy']
    ranked = rank_passages(inputs['query'], passages)
    retrieved, selected, selection = _select(ranked, passages, policy, arm)
    packed, body, packing = pack_passages(selected, inputs['budget_bytes'])
    visible = {'request': {k: v for k, v in case.items() if k != 'case_id'}, 'context_body': body}
    decision = decide(visible, agent)
    events, state = _backend(case, decision, policy)
    expected = 'refund' if case['age_days'] <= policy['window_days'] and case['amount_cents'] <= policy['max_refund_cents'] else 'deny'
    retrieved_units, packed_units = evidence_units(retrieved, policy), evidence_units(packed, policy)
    blocked = sum(event['result']['status'] == 'blocked' for event in events)
    grade = {'retrieved_units': retrieved_units, 'packed_units': packed_units,
        'retrieved_evidence_unit_recall': len(retrieved_units) / len(UNITS),
        'packed_evidence_unit_recall': len(packed_units) / len(UNITS),
        'expected_action': expected, 'decision_correct': decision['action'] == expected,
        'blocked_attempts': blocked,
        'contract_passed': len(packed_units) == len(UNITS) and decision['action'] == expected and not blocked
                           and len(state['refunds']) == int(expected == 'refund')}
    payload = {'case_id': case['case_id'], 'arm': arm, 'agent': agent, 'registration_hash': registration_hash,
        'rankings': ranked, 'retrieved_ids': [p['passage_id'] for p in retrieved],
        'selected_ids': [p['passage_id'] for p in selected], 'selection_events': selection,
        'packed_ids': [p['passage_id'] for p in packed], 'packing_events': packing,
        'packed_bytes': len(body.encode('utf-8')), 'agent_input': visible, 'decision': decision,
        'initial_state': {'refunds': []}, 'tool_events': events, 'final_state': state, 'grade': grade}
    return {'payload': payload, 'artifact_hash': canonical_hash(payload)}


def run_study(inputs=None):
    try:
        owned = json.loads(_json(example_inputs() if inputs is None else inputs))
        _validate(owned)
        protocol = {'arms': list(ARMS), 'agents': list(AGENTS), 'ranking': 'unique-ascii-term-overlap-id-tiebreak',
            'packing': 'recency-descending-id-tiebreak-whole-json-passages',
            'filter': 'trusted-active-version-and-authoritative-source-kind-then-exact-content-dedup',
            'budget_unit': 'UTF8 bytes of actual serialized context_body, excluding request and outer wrapper',
            'required_evidence_units': list(UNITS), 'agent_contract': 'require complete noncontradictory two-fact bundle',
            'backend': 'independent-window-and-amount-cap-v1', 'authority': 'local synthetic study only'}
        registration = canonical_hash({'inputs': owned, 'protocol': protocol})
        trials = [_trial(owned, case, arm, agent, registration)
                  for agent in AGENTS for arm in ARMS for case in owned['cases']]
        summary = []
        for agent in AGENTS:
            for arm in ARMS:
                grades = [t['payload']['grade'] for t in trials if t['payload']['arm'] == arm and t['payload']['agent'] == agent]
                summary = [*summary, {'agent': agent, 'arm': arm, 'case_count': len(grades),
                    **{key: sum(g[key] for g in grades) / len(grades) for key in (
                        'retrieved_evidence_unit_recall', 'packed_evidence_unit_recall')},
                    'contract_passes': sum(g['contract_passed'] for g in grades),
                    'blocked_attempts': sum(g['blocked_attempts'] for g in grades)}]
        report = {'schema': 'context-packing-study-v1', 'inputs': owned, 'protocol': protocol,
            'registration_hash': registration, 'trials': trials, 'summary': summary,
            'deployment_authorized': False, 'evidence_kind': 'executed_deterministic_mock',
            'limitations': 'Constructed cases, not population evidence. Lexical ranking and structured fact parsing '
                'are not language understanding. Metadata authority is assumed, not authenticated. Oracle uses '
                'evaluator knowledge and is not a fair deployable retrieval method. UTF8 context bytes include '
                'facts and JSON but exclude request/wrapper; not tokenizer, model cost or latency measurements. '
                'Larger k interacts with recency reordering and a fixed byte budget; prefix-preserving packing '
                'need not evict earlier evidence. Requiring both facts is this control contract, not a universal '
                'minimum-evidence theorem. Source IDs and duplicate content are distinct; coverage counts '
                'two evidence units, not duplicate documents. Local re-execution is not historical attestation.'}
        return {**report, 'report_hash': canonical_hash(report)}
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError) as error:
        raise ValueError('invalid context-packing study inputs') from error


def replay_study(report):
    owned = json.loads(_json(report))
    expected = run_study(owned['inputs'])
    _require(canonical_hash(owned) == canonical_hash(expected), 'retained study differs from complete re-execution')
    return tuple(expected['trials'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
