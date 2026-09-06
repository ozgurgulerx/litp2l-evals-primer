"""Execute and replay multi-order comparisons without claiming prose qualification."""

import argparse
from dataclasses import replace
import json
from pathlib import Path

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.cost_accounting import summarize_packet_costs
from cx_eval_lab.evidence import (
    DeterministicTestReceipt, PrerequisiteReceipt, build_evidence_receipt, canonical_hash,
)
from cx_eval_lab.order_resolution import DescriptiveResolver, FirstRecordResolver, example_cases
from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution


def _comparison(candidate):
    cases, baseline = example_cases(), DescriptiveResolver()
    manifest = replace(make_manifest(cases, baseline.name, candidate.name),
                       experiment_id='paired-resolution-' + candidate.name)
    experiment = run_paired_resolution(cases=cases, baseline_agent=baseline,
                                      candidate_agent=candidate, manifest=manifest)
    packet = experiment.to_dict()
    results = replay_packet(packet)
    candidate_results = results[len(experiment.baseline_trials):]
    checks = (('all_registered_trials_replayed', len(results) == 16),)
    test_evidence = {'checks': checks, 'packet_hash': canonical_hash(packet)}
    prerequisites = tuple(PrerequisiteReceipt(name, ((check, False),), canonical_hash({'missing': check}))
        for name, check in (('typed_tool_boundary', 'full_boundary_qualification_available'),
                            ('semantic_state_grading', 'multi_order_semantic_qualification_available')))
    receipt = build_evidence_receipt(experiment=experiment,
        deterministic_test_receipt=DeterministicTestReceipt('resolution-mock-replay', manifest.code_revision,
                                                            checks, canonical_hash(test_evidence)),
        prerequisite_receipts=prerequisites, issued_at='2026-09-06T12:00:00Z')
    if receipt.action != 'block' or receipt.authority_ceiling != 'none':
        raise ValueError('unqualified resolution comparison cannot authorize release')
    return {'candidate': candidate.name, 'packet': packet, 'test_evidence': test_evidence,
            'release_receipt': receipt.to_dict(), 'costs': summarize_packet_costs(packet),
            'candidate_contract_passes': sum(r.passed for r in candidate_results),
            'candidate_completed_tasks': sum(r.task_completed for r in candidate_results),
            'unqualified_message_trials': sum(r.unqualified_message_count for r in results)}


def run_study():
    return {'study': 'paired-order-resolution-study-v1', 'evidence_kind': 'executed_deterministic_mock',
            'deployment_authorized': False,
            'comparisons': [_comparison(FirstRecordResolver()), _comparison(DescriptiveResolver())],
            'limitations': 'Four scripted cases share one customer; two permutations are not independent '
                'samples. Structural contract only, not qualified prose. Costs/latency profile invented; '
                'actual mock elapsed time retained separately. No live models, human review, '
                'execution attestation, or deployment qualification.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new resolution artifact path.\n')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
