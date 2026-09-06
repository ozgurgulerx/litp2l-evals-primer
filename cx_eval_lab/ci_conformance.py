"""Offline software conformance checks. Never authorizes AI deployment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.evidence import canonical_hash


def verify_packet(packet, *, action, revision):
    results = replay_packet(packet['experiment'])
    receipt = packet['receipt']
    if packet['experiment']['manifest']['code_revision'] != revision:
        raise ValueError('experiment revision differs from CI checkout identity')
    expected_authority = 'lab_only' if action == 'lab_pass' else 'none'
    if receipt['action'] != action or receipt['authority_ceiling'] != expected_authority:
        raise ValueError('unexpected action or authority escalation')
    payload = {key: value for key, value in receipt.items() if key != 'receipt_hash'}
    if canonical_hash(payload) != receipt['receipt_hash']:
        raise ValueError('receipt hash mismatch')
    if receipt['raw_artifact_hash'] != canonical_hash(packet['experiment']):
        raise ValueError('receipt does not reference this experiment')
    if packet['comparison'] != receipt['comparison']:
        raise ValueError('top-level comparison differs from receipt')
    candidate = results[len(results) // 2:]
    if action in {'lab_pass', 'hold'} and not all(result.passed for result in results):
        raise ValueError('reference control contains a failed case')
    if action == 'block' and all(result.passed for result in candidate):
        raise ValueError('negative control did not exhibit a graded failure')
    return len(results)


def _write(path, value):
    with path.open('x', encoding='utf-8') as destination:
        json.dump(value, destination, indent=2, allow_nan=False)
        destination.write('\n')


def _text(value):
    """TimeoutExpired can retain bytes even when run requests text output."""
    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''


def _execute(command, record_path, expected_exit, revision):
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                   env={**os.environ, 'CXLAB_CODE_REVISION': revision})
    except (subprocess.TimeoutExpired, OSError) as error:
        record = {'returncode': None, 'expected_returncode': expected_exit,
                  'status': 'timeout' if isinstance(error, subprocess.TimeoutExpired) else 'launch_error',
                  'stdout': _text(getattr(error, 'stdout', None)),
                  'stderr': _text(getattr(error, 'stderr', None))}
        try:
            _write(record_path, record)
        except OSError as write_error:
            error.add_note(f'Command diagnostic could not be written: {type(write_error).__name__}')
        raise
    return completed


def run_conformance(output: Path, revision: str):
    if not revision or not revision.strip():
        raise ValueError('CI revision is required')
    output.mkdir(parents=True, exist_ok=False)
    configurations = (
        ('reference', 'reference', 5, 'lab_pass', 0),
        ('insufficient-evidence', 'reference', 30, 'hold', 3),
        ('policy-bypass', 'policy-bypass', 5, 'block', 2),
    )
    checks = []
    for name, candidate, minimum, action, expected_exit in configurations:
        artifact = f'{name}.json'
        command = [sys.executable, '-m', 'cx_eval_lab', 'experiment',
                   '--candidate-agent', candidate, '--minimum-independent-clusters', str(minimum),
                   '--output', str(output / artifact)]
        phase, status = 'command', 'command_error'
        try:
            completed = _execute(command, output / f'{name}-command.json', expected_exit, revision)
            phase, status = 'command_record', 'record_error'
            _write(output / f'{name}-command.json', {
                'returncode': completed.returncode, 'expected_returncode': expected_exit,
                'stdout': completed.stdout, 'stderr': completed.stderr,
            })
            phase, status = 'exit', 'unexpected_exit'
            if completed.returncode != expected_exit:
                raise ValueError(f'{name}: unexpected CLI exit {completed.returncode}')
            phase, status = 'packet', 'invalid_packet'
            packet = json.loads((output / artifact).read_text(encoding='utf-8'))
            phase, status = 'verification', 'invalid_evidence'
            count = verify_packet(packet, action=action, revision=revision)
            checks = [*checks, {'name': name, 'artifact': artifact, 'action': action,
                               'replayed_trials': count, 'artifact_hash': canonical_hash(packet)}]
        except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
                subprocess.TimeoutExpired) as error:
            if phase == 'command':
                if isinstance(error, subprocess.TimeoutExpired):
                    status = 'timeout'
                elif isinstance(error, OSError):
                    status = 'launch_error'
            failure = {'schema': 'ci-conformance-failure-v1', 'code_revision': revision,
                       'checks': checks, 'failed_control': name, 'phase': phase, 'status': status,
                       'error_type': type(error).__name__, 'deployment_authorized': False}
            try:
                _write(output / 'conformance-failure.json', failure)
            except OSError as write_error:
                error.add_note(f'Failure diagnostic could not be written: {type(write_error).__name__}')
            raise
    report = {'schema': 'ci-conformance-v1', 'code_revision': revision,
              'checks': checks, 'deployment_authorized': False,
              'meaning': 'software conformance only; no model capability or deployment qualification'}
    _write(output / 'conformance.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--code-revision', required=True)
    args = parser.parse_args()
    try:
        report = run_conformance(args.output_dir, args.code_revision)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
            subprocess.TimeoutExpired) as error:
        parser.error(f'conformance failed: {error}')
    print(f"verified {len(report['checks'])} controls; deployment_authorized=false")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
