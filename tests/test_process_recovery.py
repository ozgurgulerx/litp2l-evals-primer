"""Crash a real child process; derive failures from durable effects."""

import unittest
from pathlib import Path
import tempfile


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


if __name__ == '__main__':
    unittest.main()
