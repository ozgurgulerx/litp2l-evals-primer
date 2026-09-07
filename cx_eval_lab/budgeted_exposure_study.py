"""Fixed, replayable in-process budgeted exposure campaign; no deployment authority."""

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, replace
from pathlib import Path

from cx_eval_lab.action_budget import ActionBudget
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.exposure_control import ExposureState, transition
from cx_eval_lab.exposure_study import execute_window
from cx_eval_lab.source_provenance import capture_source_inputs


SCHEMA = 'budgeted-exposure-v1'
CAMPAIGN = 'fixed-budget-campaign-v1'


def _inventory():
    return {'sources': dict(capture_source_inputs(Path(__file__).resolve().parent.parent)),
            'interpreter': {'version': sys.version,
                            'sha256': 'sha256:' + hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()}}


def _json(value):
    """Strict finite JSON serialization also distinguishes booleans from numbers."""
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError('packet must contain finite JSON data') from error


def _artifact_without_timing(artifact):
    result = dict(artifact)
    for arm in ('baseline', 'candidate'):
        trial = artifact[arm]
        if trial is not None:
            duration = trial['elapsed_ms']
            if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
                raise ValueError('elapsed_ms must be finite and nonnegative')
            result[arm] = {**trial, 'elapsed_ms': 0}
    return result


def _summary(artifacts):
    candidates = [row['candidate'] for row in artifacts if row['candidate'] is not None]
    return {'registered_requests': len(artifacts), 'candidate_executions': len(candidates),
            'candidate_completed': sum(row['task_completed'] for row in candidates),
            'candidate_needs_review': sum(row['output']['claimed_outcome'] == 'needs_review' for row in candidates),
            'candidate_attempts': sum(event['tool'] == 'issue_refund' for row in candidates for event in row['tool_events']),
            'candidate_budget_denials': sum(event['tool'] == 'issue_refund'
                and event.get('result', {}).get('reason', '').startswith('budget_')
                for row in candidates for event in row['tool_events']),
            'candidate_commits': sum(order['state']['refund_transaction_count'] for row in candidates for order in row['orders']),
            'baseline_completed': sum(row['baseline']['task_completed'] for row in artifacts)}


def _conforms(windows):
    return ([row['before']['stage'] for row in windows] == ['shadow', 'canary', 'restricted']
            and [row['served_candidate'] for row in windows] == [0, 4, 4]
            and [row['budget_after']['charged_actions'] for row in windows] == [0, 2, 2]
            and [len(row['budget_after']['denials']) for row in windows] == [0, 2, 6]
            and [row['summary']['candidate_completed'] for row in windows] == [40, 2, 0]
            and all(row['summary']['baseline_completed'] == 40 for row in windows))


def run_study():
    """Execute only this registered program; no artifact-controlled configuration."""
    inventory = _inventory()
    state = ExposureState('cx-simulation-v1', 'baseline-v1')
    budget = ActionBudget(2, {'EUR': 9000})
    initial_state, initial_budget = asdict(state), budget.snapshot()
    windows = []
    for number in (1, 2, 3):
        before = budget.snapshot()
        window, artifacts, count = execute_window(state, number, 'healthy', action_budget=budget,
                                                  execution_namespace=CAMPAIGN)
        # Measured latency is retained but is not an action identity or a quality signal.
        hashes = [canonical_hash(_artifact_without_timing(row)) for row in artifacts]
        by_customer = {row['customer_id']: digest for row, digest in zip(artifacts, hashes, strict=True)}
        window = replace(window, observations=tuple(replace(row, artifact_id=by_customer[row.customer_id])
                                                    for row in window.observations))
        decision = transition(state, window, now=window.end)
        windows.append({'before': asdict(state), 'window': asdict(window), 'decision': asdict(decision),
                        'resume_requested': False, 'served_candidate': count, 'served_baseline': 40 - count,
                        'budget_before': before, 'budget_after': budget.snapshot(),
                        'artifacts': artifacts, 'artifact_hashes': hashes, 'summary': _summary(artifacts)})
        state = decision.state
    report = {'schema': SCHEMA, 'campaign': CAMPAIGN,
              'evidence_kind': 'executed_fixed_single_process_mock_campaign',
              'policy': {'max_actions': 2, 'currency_caps': {'EUR': 9000},
                         'scope': 'served_candidate_campaign', 'windows': [1, 2, 3],
                         'fault_intervention': 'healthy', 'resume_requested': False},
              'initial_state': initial_state, 'initial_budget': initial_budget,
              'windows': windows, 'final_state': asdict(state), 'final_budget': budget.snapshot(),
              'source_inventory': inventory, 'conformance_passed': _conforms(windows),
              'artifact_hash_semantics': 'Complete artifact with only baseline/candidate elapsed_ms set to zero.',
              'deployment_authorized': False,
              'limitations': 'Fixed deterministic agents and mock effects, not model quality or production qualification. '
              'Shared Python locks provide no crash durability or multiprocess authority. Baseline and shadow '
              'effects are isolated simulations, not evidence that real shadowing prevents writes. Budget-denied '
              'work remains unfinished; policy outcomes are not intrinsic candidate-quality estimates. '
              'Hashes and local replay establish consistency, not authenticated execution provenance.'}
    return {**report, 'report_hash': canonical_hash(report)}


def _normalized(report):
    return {**{key: value for key, value in report.items() if key != 'report_hash'},
            'windows': [{**window, 'artifacts': [_artifact_without_timing(row) for row in window['artifacts']]}
                        for window in report['windows']]}


def verify_study(report):
    """Verify current bytes then rerun fixed builtins; never execute packet content."""
    if type(report) is not dict:
        raise ValueError('packet must be an object')
    _json(report)
    if _json(report.get('source_inventory')) != _json(_inventory()):
        raise ValueError('source inventory differs from current sources/interpreter')
    if report.get('report_hash') != canonical_hash({key: value for key, value in report.items() if key != 'report_hash'}):
        raise ValueError('report hash mismatch')
    try:
        normalized = _normalized(report)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('malformed packet') from error
    # Only elapsed_ms at registered trial locations varies. Exact full JSON comparison
    # rejects extra/missing fields, identity rebinding, bool-as-int and altered evidence.
    if _json(normalized) != _json(_normalized(run_study())):
        raise ValueError('fixed builtin replay differs from retained packet')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify is not None:
        try:
            verify_study(json.loads(args.verify.read_text(encoding='utf-8')))
        except (OSError, ValueError) as error:
            parser.error(str(error))
        return 0
    if args.output.exists():
        parser.error('choose a new output path')
    report = run_study()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write('\n')
    return 0 if report['conformance_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
