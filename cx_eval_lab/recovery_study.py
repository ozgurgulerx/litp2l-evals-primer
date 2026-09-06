"""Kill and restart owned child processes; score observed durable state."""

from __future__ import annotations

import json
import argparse
import hashlib
import platform
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
import time
import tempfile

from cx_eval_lab.recovery_worker import AMOUNT, CURRENCY, ORDER, initialize, revoke, snapshot


def _interrupt(command, boundary):
    process = subprocess.Popen([*command, '--pause', boundary], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        ready, _, _ = select.select([process.stdout], [], [], 5)
        if not ready:
            raise TimeoutError("worker did not reach the registered crash boundary")
        line = process.stdout.readline()
        marker = json.loads(line)
        if marker != {"boundary": boundary, "pid": process.pid}:
            raise ValueError("unexpected worker crash-boundary marker")
        process.kill()
        process.wait(timeout=5)
        return process.pid, process.returncode, marker
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


def run_recovery_trial(directory: Path, *, boundary="after_commit", mode="reference", revoke_approval=False):
    if boundary not in {"uninterrupted", "before_commit", "after_commit", "after_checkpoint"}:
        raise ValueError("unknown crash boundary")
    if mode not in {"reference", "new-key-retry"}:
        raise ValueError("unknown recovery mode")
    database = directory / 'ledger.sqlite'
    initialize(database)
    command = [sys.executable, '-m', 'cx_eval_lab.recovery_worker', '--database', str(database)]
    interrupted_pid, returncode, marker = (
        (None, None, None) if boundary == 'uninterrupted' else _interrupt(command, boundary)
    )
    interrupted_state = snapshot(database)
    if revoke_approval:
        revoke(database)
    start = time.perf_counter()
    resumed = subprocess.run([*command, '--mode', mode], capture_output=True, text=True, timeout=5)
    elapsed = round((time.perf_counter() - start) * 1000, 3)
    response = json.loads(resumed.stdout)
    final_state = snapshot(database)
    expected_count = 0 if boundary in {'before_commit', 'uninterrupted'} and revoke_approval else 1
    payments = final_state['payments']
    correct_values = all((row['order_id'], row['amount_cents'], row['currency']) == (ORDER, AMOUNT, CURRENCY)
                         for row in payments)
    completed = any(row['status'] == 'complete' for row in final_state['checkpoints'])
    passed = (len(payments) == expected_count and correct_values and
              ((expected_count == 1 and completed and resumed.returncode == 0) or
               (expected_count == 0 and not completed and response.get('error_type') == 'PermissionError')))
    return {
        "boundary": boundary, "mode": mode, "approval_revoked_before_resume": revoke_approval,
        "interrupted_pid": interrupted_pid, "interrupted_returncode": returncode,
        "boundary_marker": marker, "state_at_interruption": interrupted_state,
        "resumed_pid": response['pid'], "resumed_returncode": resumed.returncode,
        "resumed_output": response, "recovery_elapsed_ms": elapsed,
        "final_state": final_state, "expected_effect_count": expected_count,
        "duplicate_effects": max(0, len(payments) - 1), "passed": passed,
    }


def run_study(repetitions=3):
    if type(repetitions) is not int or not 1 <= repetitions <= 20:
        raise ValueError("repetitions must be an integer from 1 to 20")
    configurations = (
        ('uninterrupted', 'reference', False), ('before_commit', 'reference', False),
        ('after_commit', 'reference', False), ('after_checkpoint', 'reference', False),
        ('after_commit', 'new-key-retry', False), ('before_commit', 'reference', True),
        ('after_commit', 'reference', True),
    )
    with tempfile.TemporaryDirectory(prefix='cx-process-study-') as directory:
        trials = tuple({"repetition": repetition, **run_recovery_trial(
            Path(directory) / f'trial-{repetition}-{index}', boundary=boundary,
            mode=mode, revoke_approval=revoked)}
            for repetition in range(repetitions)
            for index, (boundary, mode, revoked) in enumerate(configurations))
    source = Path(__file__)
    return {
        "schema": "process-recovery-study-v1", "authority": "lab_only",
        "evidence_kind": "executed_posix_process_faults_with_mock_payment_ledger",
        "manifest": {
            "python_version": platform.python_version(), "platform": platform.system(),
            "sqlite_version": sqlite3.sqlite_version, "repetitions": repetitions,
            "worker_sha256": hashlib.sha256(source.with_name('recovery_worker.py').read_bytes()).hexdigest(),
            "study_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "crash_mechanism": "Popen.kill after an observed synchronization marker",
        },
        "reference_contract_passes": sum(t['passed'] for t in trials if t['mode'] == 'reference'),
        "mutants_detected": sum(not t['passed'] for t in trials if t['mode'] == 'new-key-retry'),
        "trials": trials,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=3)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; use a new artifact path')
    try:
        report = run_study(args.repetitions)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as destination:
            json.dump(report, destination, indent=2, allow_nan=False)
            destination.write('\n')
    except (ValueError, OSError, TimeoutError, subprocess.TimeoutExpired) as error:
        parser.error(str(error))
    print(f"retained {len(report['trials'])} trials; reference passes: {report['reference_contract_passes']}; "
          f"mutants detected: {report['mutants_detected']}; authority: lab_only")
    return 0 if report['reference_contract_passes'] == 6 * args.repetitions and report['mutants_detected'] == args.repetitions else 2


if __name__ == '__main__':
    raise SystemExit(main())
