"""Replayed native-resolution slices, separating structure from qualified joint outcomes."""

import json

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.evidence import ExperimentManifest, canonical_hash
from cx_eval_lab.paired_slices import _summarize


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _labels(values):
    _require(isinstance(values, list) and all(isinstance(v, str) and v.strip() for v in values),
             'slice labels must be a list of nonempty strings')
    _require(len(values) == len(set(values)), 'slice labels must be unique')
    return values


def _validate_plan(plan, packet, manifest):
    _require(isinstance(plan, dict) and set(plan) == {'schema', 'case_labels', 'required_slices'}
             and plan['schema'] == 'resolution-slice-plan-v1', 'unsupported resolution slice plan')
    mapping = plan['case_labels']
    _require(isinstance(mapping, dict) and all(isinstance(key, str) and key.strip() for key in mapping),
             'complete case-to-feature-label mapping required')
    expected = {row['case_id'] for row in packet['baseline_trials']}
    _require(set(mapping) == expected, 'slice plan must cover exactly the registered cases')
    for values in mapping.values():
        _require(bool(_labels(values)), 'every case needs at least one feature label')
    required = _labels(plan['required_slices'])
    registered = dict(manifest.input_hashes).get('resolution-slice-plan')
    if registered is None:
        _require(not required, 'retrospective slices cannot become required gates')
        return 'retrospective_exploratory'
    _require(registered == canonical_hash(plan), 'resolution slice plan differs from manifest registration')
    return 'manifest_bound_declared'


def _strict_packet(packet):
    _require(isinstance(packet, dict) and set(packet) == {
        'manifest', 'manifest_hash', 'baseline_trials', 'candidate_trials', 'trial_artifacts'},
        'complete native paired packet required')
    schemas = {artifact['payload']['schema'] for artifact in packet['trial_artifacts']}
    _require(len(schemas) == 1 and schemas.issubset({'resolution-trial-v1', 'resolution-trial-v2'}),
             'only unmixed native resolution v1/v2 artifacts are supported')
    for artifact in packet['trial_artifacts']:
        p = artifact['payload']
        _require(type(p['identity']['trial_index']) is int, 'artifact trial index must be an exact integer')
        evaluation = p['evaluation']
        for key in ('passed', 'task_completed', 'structural_contract_passed', 'semantic_message_qualified'):
            if key in evaluation:
                _require(type(evaluation[key]) is bool, 'native evaluation decisions require booleans')
        for check in evaluation['checks']:
            _require(type(check['passed']) is bool, 'native check decisions require booleans')
        for key in ('qualified', 'passed', 'abstained'):
            if 'semantic_status' in evaluation:
                _require(type(evaluation['semantic_status'][key]) is bool, 'native semantic status requires booleans')
    for arm in ('baseline', 'candidate'):
        for row in packet[f'{arm}_trials']:
            _require(type(row['trial_index']) is int and type(row['passed']) is bool,
                     'native summary requires integer indices and boolean outcomes')
    return next(iter(schemas))


def _arm_evidence(row, result, native_semantic):
    structural = result.structural if native_semantic else result
    semantic = result.to_dict()['semantic_status'] if native_semantic else {
        'qualified': False, 'passed': False, 'abstained': False, 'reason': 'not_implemented_v1'}
    return {'summary': row, 'structural_passed': structural.passed,
            'structural_checks': [check.to_dict() for check in structural.checks],
            'semantic_status': semantic, 'joint_passed': result.passed if native_semantic else False,
            'joint_eligible': semantic['qualified'] and not semantic['abstained']}


def _outcome(baseline, candidate, eligible):
    if not eligible:
        return 'unqualified'
    if baseline and candidate:
        return 'unchanged_pass'
    if candidate:
        return 'fixed'
    return 'regressed' if baseline else 'unchanged_fail'


def _pairs(packet, results, plan, native_semantic, mode):
    rows = [*packet['baseline_trials'], *packet['candidate_trials']]
    _require(len(rows) == len(results), 'replayed result count differs from native inventory')
    indexed = {(row['arm'], row['case_id'], row['trial_index']): _arm_evidence(row, result, native_semantic)
               for row, result in zip(rows, results, strict=True)}
    pairs = []
    for row in packet['baseline_trials']:
        key = row['case_id'], row['trial_index']
        b, c = (indexed[(arm, *key)] for arm in ('baseline', 'candidate'))
        eligible = mode == 'structural' or (b['joint_eligible'] and c['joint_eligible'])
        field = 'structural_passed' if mode == 'structural' else 'joint_passed'
        # Adapt only the paired statistical projection. Preserve both original evidence objects.
        projected = [{**arm['summary'], 'passed': arm[field], 'failed_checks':
            [check['name'] for check in arm['structural_checks'] if not check['passed']]
            if mode == 'structural' else arm['summary']['failed_checks']} for arm in (b, c)]
        pairs.append({'case_id': key[0], 'trial_index': key[1], 'customer_id': row['cluster_id'],
            'slices': plan['case_labels'][key[0]], 'outcome': _outcome(b[field], c[field], eligible),
            'baseline': projected[0], 'candidate': projected[1],
            'baseline_evidence': b, 'candidate_evidence': c})
    return pairs


def _section(pairs, manifest, plan, mode):
    required = plan['required_slices']
    overall = _summarize(pairs, manifest, '__overall__', 'overall')
    labels = sorted(set(required) | {label for row in pairs for label in row['slices']})
    slices = [_summarize([r for r in pairs if label in r['slices']], manifest, label,
              'required' if label in required else 'exploratory') for label in labels]
    if mode == 'structural':
        # A v2 manifest registers JOINT quality: the structural projection is not that outcome.
        # Keep both v1/v2 structural views uniformly descriptive to avoid implicit new authority.
        overall = {**overall, 'comparison': None, 'status': 'hold'}
        slices = [{**row, 'comparison': None, 'status': 'hold'} for row in slices]
    statuses = [overall['status'], *(row['status'] for row in slices if row['membership'] == 'required')]
    status = 'block' if 'block' in statuses else 'hold' if 'hold' in statuses else 'lab_pass'
    return {'overall': overall, 'slices': slices, 'pairs': pairs, 'status': status,
            'estimand_scope': 'descriptive_structural_projection' if mode == 'structural'
                             else 'registered_joint_when_qualified'}


def derive_resolution_slice_report(packet, slice_plan, *, trusted_calibration_hashes=frozenset()):
    """Derive native structural/joint diagnostics; caller supplies historical calibration trust.

    Feature labels are an explicit analyst plan, not inferred from pass/fail. Without a
    matching manifest commitment all labels are retrospective and non-gating.
    """
    try:
        owned, plan = json.loads(json.dumps([packet, slice_plan], allow_nan=False))
        schema = _strict_packet(owned)
        manifest = ExperimentManifest(**owned['manifest'])
        binding = _validate_plan(plan, owned, manifest)
        results = replay_packet(owned, trusted_calibration_hashes=trusted_calibration_hashes)
        sections = {mode: _section(_pairs(owned, results, plan, schema == 'resolution-trial-v2', mode),
                                   manifest, plan, mode) for mode in ('structural', 'joint')}
        report = {'schema': 'resolution-slices-v1', 'packet_hash': canonical_hash(owned),
            'plan_hash': canonical_hash(plan), 'plan_binding': binding, **sections,
            'status': sections['joint']['status'], 'authority_ceiling': 'lab_only',
            'overlapping_slices_not_additive': True, 'deployment_authorized': False,
            'limitations': 'Historical replay-derived diagnostics, not a new execution, current calibration, '
                'authenticated provenance or deployment permission. A plan hash binds declared labels, '
                'not their correctness or chronology. Feature labels and required slices need independent '
                'design review. v1 has no qualified joint outcome; v2 qualified false judgments are failures, '
                'while abstention/unqualified judgments remain unknown. Known structural defects remain '
                'visible alongside unknown joint evidence. Structural projections are descriptive only. '
                'Joint intervals use the existing unqualified teaching method, not multiplicity-qualified '
                'inference. Repetitions do not increase customer independence; overlapping slices are not additive.'}
        return {**report, 'report_hash': canonical_hash(report)}
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError) as error:
        raise ValueError('malformed native paired-slice evidence') from error
