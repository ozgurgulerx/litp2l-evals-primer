"""Crash a real child process; derive failures from durable effects."""

import unittest
from pathlib import Path
import tempfile
import subprocess
import sys
import json


class ProcessRecoveryTests(unittest.TestCase):
    def test_reference_recovers_at_each_crash_boundary_without_duplicate_effects(self):
        from cx_eval_lab.recovery_study import run_recovery_trial
        for boundary in ('before_commit', 'after_commit', 'after_checkpoint'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                result = run_recovery_trial(Path(directory), boundary=boundary)
                self.assertLess(result['interrupted_returncode'], 0)
                self.assertEqual(0, result['resumed_returncode'])
                self.assertEqual(1, len(result['final_state']['payments']))
                self.assertEqual('complete', result['final_state']['checkpoints'][0]['status'])
                self.assertTrue(result['passed'])
                self.assertNotEqual(result['interrupted_pid'], result['resumed_pid'])

    def test_new_key_retry_duplicates_a_committed_effect(self):
        from cx_eval_lab.recovery_study import run_recovery_trial
        with tempfile.TemporaryDirectory() as directory:
            result = run_recovery_trial(Path(directory), boundary='after_commit', mode='new-key-retry')
            self.assertFalse(result['passed'])
            self.assertEqual(2, len(result['final_state']['payments']))
            self.assertEqual(1, result['duplicate_effects'])
            self.assertEqual([], result['state_at_interruption']['checkpoints'])

    def test_approval_revoked_before_commit_blocks_new_effect(self):
        from cx_eval_lab.recovery_study import run_recovery_trial
        with tempfile.TemporaryDirectory() as directory:
            result = run_recovery_trial(Path(directory), boundary='before_commit', revoke_approval=True)
            self.assertNotEqual(0, result['resumed_returncode'])
            self.assertEqual([], result['final_state']['payments'])
            self.assertTrue(result['passed'])

    def test_revocation_after_commit_does_not_erase_completed_effect(self):
        from cx_eval_lab.recovery_study import run_recovery_trial
        with tempfile.TemporaryDirectory() as directory:
            result = run_recovery_trial(Path(directory), boundary='after_commit', revoke_approval=True)
            self.assertEqual(0, result['resumed_returncode'])
            self.assertEqual(1, len(result['final_state']['payments']))
            self.assertTrue(result['passed'])

    def test_uninterrupted_control(self):
        from cx_eval_lab.recovery_study import run_recovery_trial
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_recovery_trial(root / 'control', boundary='uninterrupted')
            self.assertIsNone(result['interrupted_pid'])
            self.assertTrue(result['passed'])

    def test_repeated_study_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'study.json'
            command = [sys.executable, '-m', 'cx_eval_lab.recovery_study',
                       '--output', str(output), '--repetitions', '2']
            completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertTrue(output.exists(), 'study CLI must retain raw execution evidence')
            report = json.loads(output.read_text())
            self.assertEqual(14, len(report['trials']))
            self.assertEqual('lab_only', report['authority'])
            self.assertEqual(2, report['mutants_detected'])
            self.assertEqual(12, report['reference_contract_passes'])
            self.assertIn('worker_sha256', report['manifest'])
            second = subprocess.run(command, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(0, second.returncode)

    def test_idempotency_key_cannot_change_amount_or_currency(self):
        from cx_eval_lab.recovery_worker import initialize, issue_payment, OPERATION, snapshot
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'ledger.sqlite'
            initialize(database)
            issue_payment(database, OPERATION)
            for changed in ({'amount': 5000}, {'currency': 'GBP'}, {'order': 'different-order'}):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    issue_payment(database, OPERATION, **changed)
            self.assertEqual(1, len(snapshot(database)['payments']))


if __name__ == '__main__':
    unittest.main()
