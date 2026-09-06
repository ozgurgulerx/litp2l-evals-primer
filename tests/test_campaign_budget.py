"""Durable admission controls; synthetic costs, no provider calls."""

import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash


class CampaignBudgetTests(unittest.TestCase):
    def setUp(self):
        from cx_eval_lab.campaign_budget import CampaignLedger, CampaignPolicy
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'budget.sqlite'
        self.policy = CampaignPolicy('fixture-campaign', 1000, 10, 2000, 600)
        self.now = [1000]
        self.ledger = CampaignLedger.create(self.path, self.policy, clock_ms=lambda: self.now[0])
        self.digest = canonical_hash({'fixture': True})

    def reserve(self, identifier, ledger=None, digest=None):
        return (ledger or self.ledger).reserve(identifier, digest or self.digest, self.digest)

    def test_unknown_cost_keeps_reservation_after_reopen(self):
        from cx_eval_lab.campaign_budget import CampaignLedger
        self.assertTrue(self.reserve('first').admitted)
        receipt = self.ledger.finalize('first', None, '{"verdict":"abstain"}')
        self.assertEqual('unknown', receipt['state'])
        reopened = CampaignLedger.open(self.path, self.policy, clock_ms=lambda: 1001)
        self.assertEqual('estimated_budget_exhausted', self.reserve('second', reopened).reason)
        summary = reopened.snapshot()
        self.assertEqual(600, summary['held_reservations_micro_usd'])
        self.assertIsNone(summary['complete_estimate_micro_usd'])
        self.assertEqual(1, summary['admissions'])

    def test_known_cost_releases_only_unused_reservation(self):
        self.reserve('first')
        self.ledger.finalize('first', 100, '{"verdict":"pass"}')
        self.assertTrue(self.reserve('second').admitted)
        self.assertEqual(700, self.ledger.snapshot()['committed_micro_usd'])
        self.assertFalse(self.reserve('third').admitted)

    def test_duplicate_and_conflicting_attempts_never_readmit(self):
        self.reserve('first')
        self.assertEqual('invocation_already_reserved', self.reserve('first').reason)
        with self.assertRaises(ValueError):
            self.reserve('first', digest=canonical_hash({'changed': True}))
        original = self.ledger.finalize('first', 100, '{"verdict":"pass"}')
        self.assertEqual(original, self.ledger.finalize('first', 100, '{"verdict":"pass"}'))
        with self.assertRaises(ValueError):
            self.ledger.finalize('first', 99, '{"verdict":"pass"}')
        self.assertFalse(self.reserve('first').admitted)

    def test_overrun_is_recorded_not_clamped_and_stops_admission(self):
        self.reserve('first')
        receipt = self.ledger.finalize('first', 700, '{"verdict":"pass"}')
        self.assertTrue(receipt['reservation_overrun'])
        self.assertEqual(700, self.ledger.snapshot()['known_estimate_micro_usd'])
        self.assertEqual('reservation_overrun', self.reserve('second').reason)

    def test_deadline_is_admission_only_and_count_is_never_refunded(self):
        from cx_eval_lab.campaign_budget import CampaignLedger
        self.reserve('first')
        self.now[0] = 2000
        self.assertEqual('deadline_reached', self.reserve('second').reason)
        receipt = self.ledger.finalize('first', 100, '{"verdict":"pass"}')
        self.assertTrue(receipt['completed_after_deadline'])
        path = Path(self.temp.name) / 'count.sqlite'
        ledger = CampaignLedger.create(path, replace(self.policy, max_admissions=1), clock_ms=lambda: 1000)
        self.reserve('one', ledger)
        ledger.finalize('one', 0, '{}')
        self.assertEqual('admission_limit_reached', self.reserve('two', ledger).reason)

    def test_concurrent_connections_do_not_double_allocate(self):
        from cx_eval_lab.campaign_budget import CampaignLedger
        def attempt(index):
            ledger = CampaignLedger.open(self.path, self.policy, clock_ms=lambda: 1000)
            return self.reserve(str(index), ledger).admitted
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(1, sum(pool.map(attempt, range(8))))
        self.assertEqual(600, self.ledger.snapshot()['committed_micro_usd'])

    def test_crash_after_reservation_does_not_enable_automatic_retry(self):
        script = '''
import json, os, sys
from cx_eval_lab.campaign_budget import CampaignLedger, CampaignPolicy
ledger = CampaignLedger.open(sys.argv[1], CampaignPolicy(**json.loads(sys.argv[2])), clock_ms=lambda:1000)
assert ledger.reserve('crashed', sys.argv[3], sys.argv[3]).admitted
os._exit(17)
'''
        from dataclasses import asdict
        completed = subprocess.run([sys.executable, '-c', script, str(self.path),
                                    json.dumps(asdict(self.policy)), self.digest], capture_output=True)
        self.assertEqual(17, completed.returncode, completed.stderr)
        self.assertFalse(self.reserve('crashed').admitted)
        self.assertEqual('reserved', self.ledger.snapshot()['invocations'][0]['state'])
        self.assertEqual(600, self.ledger.snapshot()['held_reservations_micro_usd'])

    def test_policy_mismatch_and_invalid_values_fail_without_reset(self):
        from cx_eval_lab.campaign_budget import CampaignLedger
        for change in ({'max_estimated_micro_usd': True}, {'max_admissions': 0},
                       {'reservation_micro_usd': 1001}, {'deadline_unix_ms': -1}):
            with self.assertRaises(ValueError):
                replace(self.policy, **change)
        with self.assertRaises(ValueError):
            CampaignLedger.open(self.path, replace(self.policy, max_admissions=20))
        with self.assertRaises(FileExistsError):
            CampaignLedger.create(self.path, self.policy)
        self.reserve('first')
        for value in (True, -1, float('nan'), 10**400):
            with self.assertRaises(ValueError):
                self.ledger.finalize('first', value, '{}')
        self.assertEqual(600, self.ledger.snapshot()['held_reservations_micro_usd'])

    def test_rounding_and_missing_cost_are_explicit(self):
        from cx_eval_lab.campaign_budget import usd_to_micro
        self.assertEqual(1, usd_to_micro(0.0000001))
        self.assertEqual(360, usd_to_micro(0.00036))
        self.assertIsNone(usd_to_micro(None))
        for value in (True, -0.1, float('inf'), float('nan'), '0.01'):
            with self.assertRaises(ValueError):
                usd_to_micro(value)

    def test_cost_rounding_is_independent_of_ambient_decimal_context(self):
        from decimal import localcontext
        from cx_eval_lab.campaign_budget import usd_to_micro
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(1235, usd_to_micro(0.0012345))
            self.assertEqual(12345000000, usd_to_micro(12345.0))


if __name__ == '__main__':
    unittest.main()
