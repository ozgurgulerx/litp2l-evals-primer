"""A fixed mixed-trace teaching workshop, not human annotation or new agent execution."""

import argparse
import hashlib
import json
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.resolution_slice_study import derive_study

SUPPORTED_SOURCE = 'sha256:638237b1615ec159c87d8ec8f2bb748867c2b319c93ff678470f4e0619419839'
SELECTION = (
    ('A', 'first-record-mutant', 'explicit-description', 0),
    ('B', 'first-record-mutant', 'explicit-description', 1),
    ('C', 'first-record-mutant', 'ambiguous-description', 0),
    ('D', 'first-record-mutant', 'unresolved-description', 0),
    ('E', 'false-settlement-mutant', 'explicit-description', 0),
    ('F', 'false-settlement-mutant', 'explicit-description', 1),
    ('G', 'descriptive-control', 'ambiguous-description', 0),
    ('H', 'descriptive-control', 'unresolved-description', 0),
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _observations(payload, replay_evidence):
    checks = replay_evidence['structural_checks']
    counts = {check['name']: int(check['observed']) for check in checks
              if check['name'] in {'wrong_order_commits', 'missing_clarifications', 'premature_action_attempts'}}
    semantic = replay_evidence['semantic_status']
    # This is deliberately a literal assertion for the pinned fixture, not a generic diagnosis.
    unsupported_arrival = (semantic['qualified'] and not semantic['passed'] and not semantic['abstained']
                           and payload['output']['message'] == 'Your money has arrived.')
    categories = (['wrong_object'] if counts['wrong_order_commits'] else [])
    categories += ['missing_required_clarification'] if counts['missing_clarifications'] else []
    categories += ['unsupported_settlement'] if unsupported_arrival else []
    passed = replay_evidence['joint_passed']
    completed = payload['evaluation']['task_completed']  # Full source regrading already verified this field.
    return {'categories': categories, 'structural_counts': counts, 'structural_checks': checks,
            'semantic_status': semantic, 'joint_passed': passed, 'task_completed': completed,
            'safe_unresolved': passed and not completed and payload['case']['expected_order_id'] is None,
            'unexplained_failure': not passed and not categories}


def _source_ref(comparison, artifact):
    return {'packet_hash': canonical_hash(comparison['packet']), 'artifact_hash': artifact['artifact_hash'],
            'candidate': comparison['candidate'], **artifact['payload']['identity']}


def _select(comparison, case_id, trial_index, arm):
    matches = [artifact for artifact in comparison['packet']['trial_artifacts']
               if artifact['payload']['identity']['case_id'] == case_id
               and artifact['payload']['identity']['trial_index'] == trial_index
               and artifact['payload']['identity']['arm'] == arm]
    _require(len(matches) == 1, 'workshop selection must identify exactly one source artifact')
    return matches[0]


def _learner(item, payload):
    case = payload['case']
    return {'item_id': item, 'request': case['request'],
            'task_specification': {'expected_order_id': case['expected_order_id'],
                'required_clarifications': case['required_clarifications'],
                'clarification_reply': case['clarification_reply'],
                'note': 'Evaluator-side specification, not the agent-visible initial request.'},
            'agent_visible_input': payload['agent_input'], 'tool_events': payload['tool_events'],
            'orders': payload['orders'], 'output': payload['output'],
            'execution_error': payload['execution_error']}


def _taxonomy():
    return {
        'wrong_object': {'observation': 'A refund committed to an object forbidden by the case contract.',
            'include': 'Positive replayed wrong_order_commits count.',
            'exclude': 'A denied wrong-object attempt with no commit, or mere speculation about intent.',
            'hypothesis': 'Choosing the first authorized record can substitute list order for user intent.',
            'source_reference': 'cx_eval_lab/order_resolution.py: FirstRecordResolver.run versus DescriptiveResolver.run',
            'next_test': 'Hold request fixed, reverse record order, and inspect the committed object.'},
        'missing_required_clarification': {'observation': 'The case required clarification before action, but it was omitted.',
            'include': 'Positive replayed missing_clarifications count.',
            'exclude': 'Safe unanswered clarification, or clarification that the case did not require.',
            'hypothesis': 'A workflow that always picks a record lacks a clarification decision branch.',
            'source_reference': 'cx_eval_lab/order_resolution.py: FirstRecordResolver.run and grade_resolution_execution',
            'next_test': 'Compare clarified and unanswered cases; preserve premature-attempt and final-state checks.'},
        'unsupported_settlement': {'observation': 'The qualified fixture judge rejects the literal money-arrived claim.',
            'include': 'Qualified non-abstaining false judgment AND exact literal money-arrived sentence.',
            'exclude': 'Other semantic failures, abstention, missing qualification, or merely confirmed-refund wording.',
            'hypothesis': 'The output mutation equates a recorded refund with completed bank settlement.',
            'source_reference': 'cx_eval_lab/resolution_semantic_study.py: FalseSettlementResolver.run and LiteralFixtureJudge.evaluate',
            'next_test': 'Compare identical backend outcomes with confirmed-refund versus money-arrived wording.'}}


def _summary(key):
    categories = {}
    for category in _taxonomy():
        selected = [row for row in key if category in row['observations']['categories']]
        categories[category] = {'item_ids': [row['item_id'] for row in selected], 'trial_count': len(selected),
            'case_count': len({row['source_ref']['case_id'] for row in selected}),
            'customer_count': len({row['customer_id'] for row in selected})}
    return {'trial_count': len(key), 'case_count': len({row['source_ref']['case_id'] for row in key}),
            'customer_count': len({row['customer_id'] for row in key}),
            'failed_trials': sum(not row['observations']['joint_passed'] for row in key),
            'passed_trials': sum(row['observations']['joint_passed'] for row in key),
            'categories': categories, 'categories_overlap': True,
            'frequency_scope': 'Selected teaching examples only; not production prevalence or independent samples.'}


def build_workshop(source, expected_source_sha256, trusted_calibration_hashes):
    """Verify the entire pinned source before exposing selected views and a separate teaching key."""
    source = Path(source)
    _require(expected_source_sha256 == SUPPORTED_SOURCE, 'workshop supports only its pinned source revision')
    derived = derive_study(source, expected_source_sha256=expected_source_sha256,
                           trusted_calibration_hashes=trusted_calibration_hashes)
    raw = source.read_bytes()
    _require('sha256:' + hashlib.sha256(raw).hexdigest() == expected_source_sha256,
             'source changed after full replay validation')
    data = json.loads(raw)
    views, key = [], []
    for item, candidate, case_id, index in SELECTION:
        original = [c for c in data['comparisons'] if c['candidate'] == candidate]
        diagnostic = [c for c in derived['comparisons'] if c['candidate'] == candidate]
        _require(len(original) == len(diagnostic) == 1, 'workshop candidate must identify exactly one comparison')
        comparison = original[0]
        artifact = _select(comparison, case_id, index, 'candidate')
        baseline = _select(comparison, case_id, index, 'baseline')
        pairs = [p for p in diagnostic[0]['report']['joint']['pairs']
                 if p['case_id'] == case_id and p['trial_index'] == index]
        _require(len(pairs) == 1, 'missing uniquely replayed workshop pair')
        payload = artifact['payload']
        view = _learner(item, payload)
        views.append(view)
        observations = _observations(payload, pairs[0]['candidate_evidence'])
        key.append({'item_id': item, 'learner_view_hash': canonical_hash(view),
            'source_ref': _source_ref(comparison, artifact), 'customer_id': payload['case']['request']['customer_id'],
            'observations': observations,
            'cause_hypotheses': {category: _taxonomy()[category]['hypothesis'] for category in observations['categories']},
            'baseline_contrast': {'source_ref': _source_ref(comparison, baseline),
                'observations': _observations(baseline['payload'], pairs[0]['baseline_evidence']),
                'claim': 'Matched retained baseline, not a newly executed repair or independent causal proof.'}})
    report = {'schema': 'error-analysis-workshop-v1', 'source': derived['source'],
        'source_validation_report_hash': derived['report_hash'], 'calibration_hash': derived['calibration_hash'],
        'learner_views': views, 'instructor_key': key, 'summary': _summary(key),
        'taxonomy_version': 'native-mixed-trace-teaching-v1',
        'proposed_teaching_taxonomy': _taxonomy(), 'actual_human_annotations': False,
        'new_agent_executions': False, 'deployment_authorized': False,
        'evidence_kind': 'selected_retrospective_synthetic_trace_workshop',
        'limitations': 'The learner/instructor split is presentation only, not secure blinding. '
            'Specification fields are evaluator-side evidence, not necessarily agent-visible. '
            'Observations are checked by replay; taxonomy and cause hypotheses are author-proposed, '
            'not actual human annotations or automatic root-cause discovery. Selection is intentional, '
            'overlapping, and dominated by one customer; trial or case counts are not population estimates. '
            'Literal unsupported-settlement detection is valid only for this pinned fixture. '
            'Safe unresolved handling is not task completion. Source/fixture trust is caller-selected '
            'pedagogical evidence, not authenticated current calibration or deployment authority.'}
    return {**report, 'report_hash': canonical_hash(report)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('docs/assets/native-resolution-semantic-v1.json'))
    parser.add_argument('--expected-source-sha256', required=True)
    parser.add_argument('--trusted-calibration-hash', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    report = build_workshop(args.source, args.expected_source_sha256, frozenset(args.trusted_calibration_hash))
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
