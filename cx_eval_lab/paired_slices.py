"""Replayed paired slice diagnostics; teaching intervals never authorize deployment."""

import argparse
import json
from dataclasses import dataclass, replace
from pathlib import Path

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.evidence import ExperimentManifest, canonical_hash
from cx_eval_lab.models import RefundCase
from cx_eval_lab.runner import DEFAULT_MEASUREMENT_PROFILE, run_paired_experiment
from cx_eval_lab.statistics import PairedTrial, paired_non_inferiority


def _required(values):
    if (not isinstance(values, tuple) or any(not isinstance(v, str) or not v.strip() for v in values)
            or len(set(values)) != len(values)):
        raise ValueError('required slices must be a tuple of unique nonempty labels')
    return tuple(sorted(values))


def slice_policy_hash(required_slices):
    return canonical_hash({'schema': 'paired-slice-policy-v1', 'required_slices': list(_required(required_slices))})


def _validate(packet, required, trusted):
    if set(packet) != {'manifest', 'manifest_hash', 'baseline_trials', 'candidate_trials', 'trial_artifacts'}:
        raise ValueError('only complete legacy paired packets are supported')
    manifest = ExperimentManifest(**packet['manifest'])
    registered = dict(manifest.input_hashes).get('slice-policy')
    if registered != slice_policy_hash(required) and (registered is not None or required):
        raise ValueError('required slices must match the pre-execution registered slice policy')
    cases = {}
    for artifact in packet['trial_artifacts']:
        payload = artifact['payload']
        if payload['schema'] != 'refund-trial-v1':
            raise ValueError('only refund-trial-v1 slice metadata is supported')
        if type(payload['identity']['trial_index']) is not int:
            raise ValueError('artifact trial index requires an exact integer')
        case = RefundCase.from_dict(payload['case'])
        if len(case.slices) != len(set(case.slices)):
            raise ValueError('case slice labels must be unique')
        if case.case_id in cases and cases[case.case_id] != case.to_dict():
            raise ValueError('case, customer or slices changed between arms/repetitions')
        cases[case.case_id] = case.to_dict()
    for arm in ('baseline', 'candidate'):
        for row in packet[f'{arm}_trials']:
            if type(row['trial_index']) is not int or type(row['passed']) is not bool:
                raise ValueError('trial index and passed require exact integer/boolean types')
    replay_packet(packet, trusted_calibration_hashes=trusted)
    return manifest, cases


def _pair_rows(packet, cases):
    indexed = {arm: {(row['case_id'], row['trial_index']): row for row in packet[f'{arm}_trials']}
               for arm in ('baseline', 'candidate')}
    rows = []
    for key in sorted(indexed['baseline']):
        baseline, candidate = (indexed[arm][key] for arm in ('baseline', 'candidate'))
        eligible = all('customer_message_qualified' not in row['failed_checks'] for row in (baseline, candidate))
        outcome = ('unqualified' if not eligible else
                   'unchanged_pass' if baseline['passed'] and candidate['passed'] else
                   'fixed' if candidate['passed'] else
                   'regressed' if baseline['passed'] else 'unchanged_fail')
        rows.append({'case_id': key[0], 'trial_index': key[1], 'customer_id': baseline['cluster_id'],
                     'slices': cases[key[0]]['slices'], 'outcome': outcome,
                     'baseline': baseline, 'candidate': candidate})
    return rows


def _summarize(rows, manifest, label, membership):
    eligible = [row for row in rows if row['outcome'] != 'unqualified']
    changes = {name: [{'case_id': r['case_id'], 'trial_index': r['trial_index']} for r in rows if r['outcome'] == name]
               for name in ('fixed', 'regressed', 'unchanged_pass', 'unchanged_fail', 'unqualified')}
    count = len(eligible)
    baseline = sum(row['baseline']['passed'] for row in eligible) / count if count else None
    candidate = sum(row['candidate']['passed'] for row in eligible) / count if count else None
    comparison = None
    clusters = sorted({row['customer_id'] for row in rows})
    cluster_delta = None
    if rows and count == len(rows):
        means = [sum(int(r['candidate']['passed']) - int(r['baseline']['passed'])
                     for r in rows if r['customer_id'] == customer)
                 / sum(r['customer_id'] == customer for r in rows) for customer in clusters]
        cluster_delta = sum(means) / len(means)
    # Never silently remove unqualified pairs from the registered inference population.
    if len(clusters) >= 2 and count == len(rows):
        comparison = paired_non_inferiority(
            tuple(PairedTrial(**row['baseline']) for row in rows),
            tuple(PairedTrial(**row['candidate']) for row in rows),
            margin=manifest.non_inferiority_margin, confidence_level=manifest.confidence_level,
            minimum_independent_clusters=manifest.minimum_independent_clusters).to_dict()
    status = ('hold' if comparison is None or comparison['status'] == 'inconclusive' else
              'block' if comparison['status'] == 'fail' else 'lab_pass')
    return {'slice': label, 'membership': membership, 'case_count': len({r['case_id'] for r in rows}),
            'pair_count': len(rows), 'customer_count': len({r['customer_id'] for r in rows}),
            'eligible_pair_count': count, 'eligible_customer_count': len({r['customer_id'] for r in eligible}),
            'changes': changes, 'baseline_rate': baseline, 'candidate_rate': candidate,
            'rate_population': 'qualified pairs only; descriptive, not a missingness adjustment',
            'trial_weighted_delta': candidate - baseline if count else None,
            'cluster_weighted_delta': cluster_delta,
            'comparison': comparison, 'status': status,
            'issues': ['missing_slice'] if not rows else ['unqualified_pairs'] if count != len(rows) else []}


def derive_slice_report(packet, required_slices=(), *, trusted_calibration_hashes=frozenset()):
    """Re-grade complete legacy artifacts; slice metadata comes from the case, not summaries.

    Trust anchors/issuer authentication and current calibration remain caller concerns.
    Registered required slices restrict this diagnostic, not an application release.
    """
    required = _required(required_slices)
    try:
        owned = json.loads(json.dumps(packet, allow_nan=False))
        manifest, cases = _validate(owned, required, trusted_calibration_hashes)
        pairs = _pair_rows(owned, cases)
        overall = _summarize(pairs, manifest, '__overall__', 'overall')
        labels = sorted(set(required) | {s for row in pairs for s in row['slices']})
        slices = [_summarize([row for row in pairs if label in row['slices']], manifest, label,
                            'required' if label in required else 'exploratory') for label in labels]
        statuses = [overall['status'], *(row['status'] for row in slices if row['membership'] == 'required')]
        status = 'block' if 'block' in statuses else 'hold' if 'hold' in statuses else 'lab_pass'
        report = {'schema': 'paired-slices-v1', 'packet_hash': canonical_hash(owned),
            'required_slices': list(required), 'slice_policy_hash': dict(manifest.input_hashes).get('slice-policy'),
            'overall': overall, 'slices': slices, 'pairs': pairs, 'status': status,
            'overlapping_slices_not_additive': True, 'authority_ceiling': 'lab_only',
            'deployment_authorized': False,
            'limitations': 'Replayed local grades, not execution provenance or current qualification. '
                'Required means locally registered by hash, not externally timestamped. Trial-weighted '
                'rates and equal-customer-weighted deltas use different estimands. Intervals use the '
                'existing unqualified teaching method; no joint/multiplicity-qualified inference. '
                'Exploratory slices never gate. Unqualified pairs may also contain known failed checks; '
                'those checks remain visible and are not erased or equated with a known outcome.'}
        return {**report, 'report_hash': canonical_hash(report)}
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError) as error:
        raise ValueError('malformed legacy paired-slice evidence') from error


@dataclass(frozen=True)
class SliceControl:
    """Deliberate visible-request output-enum bug; transaction still executes."""
    candidate: bool
    unqualified: bool = False

    def run(self, request, tools):
        output = ReferenceSupportAgent().run(request, tools)
        if self.unqualified:
            return replace(output, message='A custom unqualified explanation.', message_template_id=None)
        protected = 'special request' in request.utterance
        return replace(output, claimed_outcome='not_refunded') if protected == self.candidate else output


def run_study(*, unqualified_candidate=False, required_slices=('risk:protected',)):
    required = _required(required_slices)
    cases = tuple(RefundCase(f'case-{i}', 'customer-shared' if i < 2 else f'customer-{i}',
        f'order-{i}', 'Please refund this special request.' if i == 3 else 'Please refund this ordinary request.',
        4000, True, 10000, 'refunded', ('all', 'risk:protected' if i == 3 else 'risk:general')) for i in range(4))
    manifest = ExperimentManifest(experiment_id='paired-slice-control-v1', created_at='2026-09-07T00:00:00Z',
        valid_until='2026-10-07T00:00:00Z', code_revision='working-tree-unpinned',
        model_id='deterministic-no-model', prompt_version='visible-utterance-enum-mutant-v1',
        tool_version='typed-refund-tools-v1', dataset_version='refund-v1', evaluator_version='refund-evaluators-v1',
        policy_version='refund-gate-v1', environment_version='python-3.12',
        population_hash=canonical_hash([[c.case_id, c.customer_id, list(c.slices)] for c in cases]),
        repetitions=2, measurement_kind='synthetic', estimand='candidate_minus_baseline_verified_success',
        statistical_method='clustered_normal_interval', non_inferiority_margin=0.03, confidence_level=0.95,
        minimum_independent_clusters=30, sequential_policy='fixed_sample_no_interim_looks',
        input_hashes=(('dataset', canonical_hash([c.to_dict() for c in cases])),
                      ('slice-policy', slice_policy_hash(required))), invalidation_rules=('source_or_dataset_or_slice_policy_change',))
    packet = run_paired_experiment(baseline_agent=SliceControl(False),
        candidate_agent=SliceControl(True, unqualified_candidate), cases=cases, manifest=manifest,
        baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
        candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE).to_dict()
    report = derive_slice_report(packet, required)
    return {'schema': 'paired-slice-study-v1', 'evidence_kind': 'executed_deterministic_mock',
            'deployment_authorized': False, 'packet': packet, 'report': report,
            'protocol': {'unqualified_candidate': unqualified_candidate, 'required_slices': list(required),
                         'baseline': 'incorrect outcome enum on ordinary requests',
                         'candidate': 'incorrect outcome enum on special requests',
                         'all_tools': 'actual reference workflow in isolated mock state',
                         'measurement': 'invented default profile; no model/latency/cost population claim'}}


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
