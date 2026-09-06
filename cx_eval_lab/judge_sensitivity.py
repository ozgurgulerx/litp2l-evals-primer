"""Executed deterministic judge controls, not observations of LLM or human bias."""

import argparse
import itertools
import json
import re
from collections import Counter
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash

JUDGES = ('reference', 'first-slot', 'length', 'rubric-keyword', 'length-clone')
SPECIAL = ('tie', 'both_unacceptable', 'abstain')
PADDING = ' Thank you.' * 5
CRITERION = ('truth against the supplied current refund state. Ignore polite padding. Return A or B '
    'when exactly one answer states the supported status; return tie when both do; return '
    'both_unacceptable when neither does; return abstain when evidence is missing. '
    'Return only verdict and a brief rationale.')
RUBRICS = ({'rubric_id': 'r0', 'text': 'Assess ' + CRITERION},
           {'rubric_id': 'r1', 'text': 'Evaluate ' + CRITERION})


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(value, keys):
    _require(isinstance(value, dict) and set(value) == set(keys), 'exact schema fields required')


def _identifier(value):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value), 'opaque identifier required')


def _clone(value):
    return json.loads(json.dumps(value, allow_nan=False))


def example_inputs():
    conditions = [('pending', ('pending', 'settled')), ('settled', ('pending', 'settled')),
                  ('pending', ('pending', 'pending')), ('pending', ('settled', 'settled')),
                  (None, ('pending', 'settled'))]
    return {'cases': [{'case_id': f'C{i + 1:02}', 'status': state,
        'answers': [{'answer_id': f'Q{i * 2 + j + 1:02}', 'claim': claim, 'base_text': f'Status: {claim}.'}
                    for j, claim in enumerate(claims)]} for i, (state, claims) in enumerate(conditions)],
        'rubrics': [dict(r) for r in RUBRICS], 'padding': PADDING,
        'orders': [0, 1], 'styles': ['brief', 'pad0', 'pad1'], 'judges': list(JUDGES)}


def _validate(inputs):
    _fields(inputs, ('cases', 'rubrics', 'padding', 'orders', 'styles', 'judges'))
    _require(inputs['rubrics'] == list(RUBRICS) and inputs['padding'] == PADDING, 'registered rubric/padding required')
    _require(inputs['orders'] == [0, 1] and all(type(o).__name__ == 'int' for o in inputs['orders']), 'exact order indices required')
    _require(inputs['styles'] == ['brief', 'pad0', 'pad1'] and inputs['judges'] == list(JUDGES), 'fixed factorial/control inventory required')
    _require(isinstance(inputs['cases'], list) and len(inputs['cases']) == 5, 'five authored cases required')
    cases, answers = set(), set()
    for case in inputs['cases']:
        _fields(case, ('case_id', 'status', 'answers'))
        _identifier(case['case_id'])
        _require(case['case_id'] not in cases, 'duplicate case')
        cases = cases | {case['case_id']}
        _require(case['status'] is None or isinstance(case['status'], str) and case['status'] in ('pending', 'settled'), 'unknown evidence state')
        _require(isinstance(case['answers'], list) and len(case['answers']) == 2, 'two answers required')
        for answer in case['answers']:
            _fields(answer, ('answer_id', 'claim', 'base_text'))
            _identifier(answer['answer_id'])
            _require(answer['answer_id'] not in answers, 'duplicate answer identity')
            answers = answers | {answer['answer_id']}
            _require(answer['claim'] in ('pending', 'settled')
                     and answer['base_text'] == f"Status: {answer['claim']}.", 'claim/base-text inconsistency')


def _expected(case):
    # Reference labels use declared, validated claims, not the runtime text parser.
    if case['status'] is None:
        return {'kind': 'abstain'}
    supported = [a['answer_id'] for a in case['answers'] if a['claim'] == case['status']]
    if len(supported) == 1:
        return {'kind': 'answer', 'answer_id': supported[0]}
    return {'kind': 'tie' if supported else 'both_unacceptable'}


def build_presentations(inputs):
    owned = _clone(inputs)
    _validate(owned)
    result = []
    for case, order, style, rubric in itertools.product(owned['cases'], owned['orders'], owned['styles'], owned['rubrics']):
        bodies = [a['base_text'] + (owned['padding'] if style == f'pad{i}' else '') for i, a in enumerate(case['answers'])]
        indices = (0, 1) if order == 0 else (1, 0)
        slot_map = {slot: case['answers'][index]['answer_id'] for slot, index in zip(('A', 'B'), indices, strict=True)}
        request = {'evidence_status': case['status'], 'answers': {slot: bodies[index] for slot, index in zip(('A', 'B'), indices, strict=True)},
                   'rubric': rubric['text']}
        metadata = {'case_id': case['case_id'], 'status': case['status'], 'answers': case['answers'],
            'order': order, 'style': style, 'rubric_id': rubric['rubric_id'], 'slot_map': slot_map,
            'expected_outcome': _expected(case), 'answer_character_lengths': {slot: len(body) for slot, body in request['answers'].items()}}
        view = {'view_id': f"{case['case_id']}/o{order}/{style}/{rubric['rubric_id']}",
                'judge_request': request, 'evaluator_metadata': metadata}
        result = [*result, {**view, 'view_hash': canonical_hash(view)}]
    return result


def normalize_verdict(raw, slot_map):
    _fields(slot_map, ('A', 'B'))
    for identifier in slot_map.values():
        _identifier(identifier)
    _require(slot_map['A'] != slot_map['B'], 'distinct answer IDs required')
    _fields(raw, ('verdict', 'rationale'))
    _require(isinstance(raw['verdict'], str) and raw['verdict'] in ('A', 'B', *SPECIAL), 'typed verdict required')
    _require(isinstance(raw['rationale'], str) and 0 < len(raw['rationale']) <= 1000, 'bounded rationale required')
    return {'kind': 'answer', 'answer_id': slot_map[raw['verdict']]} if raw['verdict'] in ('A', 'B') else {'kind': raw['verdict']}


def execute_control(judge, request):
    """Consumes only request evidence, visible A/B text and full rubric wording."""
    _require(judge in JUDGES, 'unknown control')
    _fields(request, ('evidence_status', 'answers', 'rubric'))
    _fields(request['answers'], ('A', 'B'))
    _require(request['evidence_status'] in ('pending', 'settled', None), 'unknown evidence state')
    _require(request['rubric'] in [r['text'] for r in RUBRICS], 'registered equivalent rubric required')
    _require(all(isinstance(v, str) and 0 < len(v) <= 1000 for v in request['answers'].values()), 'bounded visible answers required')
    if judge == 'reference':
        parsed = {slot: re.fullmatch(r'Status: (pending|settled)\.(?: Thank you\.)*', text)
                  for slot, text in request['answers'].items()}
        _require(all(parsed.values()), 'reference parser supports registered grammar only')
        supported = [slot for slot, match in parsed.items() if match is not None and match.group(1) == request['evidence_status']]
        verdict = ('abstain' if request['evidence_status'] is None else supported[0] if len(supported) == 1
                   else 'tie' if len(supported) == 2 else 'both_unacceptable')
    elif judge == 'first-slot':
        verdict = 'A'
    elif judge in ('length', 'length-clone'):
        verdict = 'A' if len(request['answers']['A']) >= len(request['answers']['B']) else 'B'
    else:
        verdict = 'A' if 'Assess' in request['rubric'] else 'B'
    return {'verdict': verdict, 'rationale': f'Executed deterministic {judge} teaching control.'}


def _grade(outcome, metadata):
    selected = outcome['kind'] == 'answer'
    claims = {a['answer_id']: a['claim'] for a in metadata['answers']}
    return {'protocol_correct': outcome == metadata['expected_outcome'],
        'selected_unsupported_known_state': selected and metadata['status'] is not None and claims[outcome['answer_id']] != metadata['status'],
        'selected_without_evidence': selected and metadata['status'] is None}


def _metrics(rows):
    nonabstained = [r for r in rows if r['normalized_outcome']['kind'] != 'abstain']
    return {'total': len(rows), 'case_count': len({r['case_id'] for r in rows}),
        'protocol_correct': sum(r['grade']['protocol_correct'] for r in rows),
        'nonabstained': len(nonabstained), 'selected_answer': sum(r['normalized_outcome']['kind'] == 'answer' for r in rows),
        'correctness_among_nonabstained': sum(r['grade']['protocol_correct'] for r in nonabstained) / len(nonabstained) if nonabstained else None,
        'selected_unsupported_known_state': sum(r['grade']['selected_unsupported_known_state'] for r in rows),
        'selected_without_evidence': sum(r['grade']['selected_without_evidence'] for r in rows)}


def _trial(judge, view, registration):
    raw = execute_control(judge, view['judge_request'])
    outcome = normalize_verdict(raw, view['evaluator_metadata']['slot_map'])
    payload = {'trial_id': f"{judge}/{view['view_id']}", 'judge': judge, 'view_id': view['view_id'], 'view_hash': view['view_hash'],
        'case_id': view['evaluator_metadata']['case_id'], 'registration_hash': registration,
        'judge_request': view['judge_request'], 'request_hash': canonical_hash(view['judge_request']),
        'raw_output': raw, 'normalized_outcome': outcome, 'grade': _grade(outcome, view['evaluator_metadata'])}
    return {'payload': payload, 'artifact_hash': canonical_hash(payload)}


def _contrast(left, right):
    return {'left_trial_id': left['payload']['trial_id'], 'right_trial_id': right['payload']['trial_id'],
        'left_artifact_hash': left['artifact_hash'], 'right_artifact_hash': right['artifact_hash'],
        'left_outcome': left['payload']['normalized_outcome'], 'right_outcome': right['payload']['normalized_outcome'],
        'flipped': left['payload']['normalized_outcome'] != right['payload']['normalized_outcome']}


def _contrasts(judge, trials, views):
    by_view = {t['payload']['view_id']: t for t in trials if t['payload']['judge'] == judge}
    index = {(m['case_id'], m['order'], m['style'], m['rubric_id']): by_view[v['view_id']]
             for v in views for m in (v['evaluator_metadata'],)}
    contrasts = {factor: [] for factor in ('order', 'length', 'rubric')}
    for key, left in index.items():
        case, order, style, rubric = key
        targets = []
        if order == 0:
            targets.append(('order', (case, 1, style, rubric)))
        if style == 'brief':
            targets.extend(('length', (case, order, other, rubric)) for other in ('pad0', 'pad1'))
        if rubric == 'r0':
            targets.append(('rubric', (case, order, style, 'r1')))
        for factor, right_key in targets:
            contrasts[factor] = [*contrasts[factor], _contrast(left, index[right_key])]
    return {factor: {'total': len(rows), 'flips': sum(r['flipped'] for r in rows), 'comparisons': rows}
            for factor, rows in contrasts.items()}


def _panel(trials, views):
    lookup = {(t['payload']['judge'], t['payload']['view_id']): t for t in trials}
    rows = []
    for view in views:
        members = [lookup[(j, view['view_id'])] for j in ('reference', 'length', 'length-clone')]
        votes = [t['payload']['normalized_outcome'] for t in members]
        counts = Counter(canonical_hash(v) for v in votes)
        outcome = next((v for v in votes if counts[canonical_hash(v)] >= 2), {'kind': 'abstain'})
        rows = [*rows, {'view_id': view['view_id'], 'case_id': view['evaluator_metadata']['case_id'],
            'member_trials': [{'trial_id': t['payload']['trial_id'], 'artifact_hash': t['artifact_hash']} for t in members],
            'votes': votes, 'normalized_outcome': outcome, 'grade': _grade(outcome, view['evaluator_metadata'])}]
    return {'members': ['reference', 'length', 'length-clone'], 'rule': 'at least two identical normalized outcomes, else abstain',
            'rows': rows, 'metrics': _metrics(rows)}


def run_study(inputs=None):
    owned = _clone(example_inputs() if inputs is None else inputs)
    views = build_presentations(owned)
    protocol = {'schema': 'fixed-five-case-judge-sensitivity-v1', 'controls': {
        'reference': 'strict visible grammar parser against evidence status', 'first-slot': 'always A',
        'length': 'longest actual visible character count, tie A', 'length-clone': 'separate call of identical length algorithm',
        'rubric-keyword': 'A if visible rubric contains Assess, otherwise B'},
        'transform': 'order permutation; neutral literal padding preserves registered status grammar',
        'contrasts': {'order': 'swap holding case/style/rubric fixed', 'length': 'each pad vs brief holding case/order/rubric fixed',
                      'rubric': 'r1 vs r0 holding case/order/style fixed'},
        'normalization': 'A/B mapped to opaque answer ID before contrasts or votes; special verdicts kept separate',
        'authority': 'executed local deterministic controls only'}
    registration = canonical_hash({'inputs': owned, 'protocol': protocol})
    trials = [_trial(judge, view, registration) for judge in JUDGES for view in views]
    panel = _panel(trials, views)
    errors = {judge: sorted(t['payload']['view_id'] for t in trials if t['payload']['judge'] == judge
                            and not t['payload']['grade']['protocol_correct']) for judge in ('length', 'length-clone')}
    report = {'schema': 'judge-sensitivity-v1', 'inputs': owned, 'protocol': protocol, 'registration_hash': registration,
        'presentations': views, 'trials': trials,
        'metrics': {j: _metrics([t['payload'] for t in trials if t['payload']['judge'] == j]) for j in JUDGES},
        'contrasts': {j: _contrasts(j, trials, views) for j in JUDGES}, 'panel': panel,
        'clone_error_overlap': {'length_error_view_ids': errors['length'], 'clone_error_view_ids': errors['length-clone'],
            'panel_error_view_ids': sorted(r['view_id'] for r in panel['rows'] if not r['grade']['protocol_correct']),
            'interpretation': 'identical algorithm clones, not independently calibrated evaluators'},
        'deployment_authorized': False, 'evidence_kind': 'executed_deterministic_judge_controls',
        'limitations': 'Five authored cases, sixty factor views and three hundred control calls are not independent '
            'population observations. Rubric equivalence and neutral padding hold only for this narrow grammar. '
            'No LLMs, humans or provider adapter were evaluated. Invariance is not correctness; stable wrong '
            'answers remain wrong. A panel of algorithm clones does not create independent evidence. No '
            'confidence interval or deployment authority is granted. Hash binding and replay do not authenticate '
            'historical registration or establish semantic validity outside these supplied fixtures.'}
    return {**report, 'report_hash': canonical_hash(report)}


def replay_study(report):
    owned = _clone(report)
    _require(isinstance(owned, dict) and 'inputs' in owned, 'retained inputs required')
    expected = run_study(owned['inputs'])
    _require(canonical_hash(owned) == canonical_hash(expected), 'retained study differs from complete control re-execution')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    with args.output.open('x') as stream:
        stream.write(json.dumps(run_study(), indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
