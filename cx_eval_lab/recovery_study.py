"""Kill and restart owned child processes; score observed durable state."""

from __future__ import annotations

import json
from pathlib import Path
import select
import subprocess
import sys
import time

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
    if boundary not in {"before_commit", "after_commit", "after_checkpoint"}:
        raise ValueError("unknown crash boundary")
    if mode not in {"reference", "new-key-retry"}:
        raise ValueError("unknown recovery mode")
    database = directory / 'ledger.sqlite'
    initialize(database)
    command = [sys.executable, '-m', 'cx_eval_lab.recovery_worker', '--database', str(database)]
    interrupted_pid, returncode, marker = _interrupt(command, boundary)
    interrupted_state = snapshot(database)
    if revoke_approval:
        revoke(database)
    start = time.perf_counter()
    resumed = subprocess.run([*command, '--mode', mode], capture_output=True, text=True, timeout=5)
    elapsed = round((time.perf_counter() - start) * 1000, 3)
    response = json.loads(resumed.stdout)
    final_state = snapshot(database)
    expected_count = 0 if boundary == 'before_commit' and revoke_approval else 1
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
