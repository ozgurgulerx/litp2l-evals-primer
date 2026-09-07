import tempfile
import unittest
from pathlib import Path

from cx_eval_lab.durable_completion import CompletionJournal
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.exposure_study import FaultInjectedCandidate, case_from_plan, build_window_plan
from cx_eval_lab.exposure_control import ExposureState


class WindowCompletionTests(unittest.TestCase):
    def test_bound_batch_missing_completed_and_identity_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = DurableCampaign.initialize(Path(directory) / 'effects', campaign_id='test',
                max_actions=2, currency_caps={'EUR': 9000})
            journal = CompletionJournal.initialize(Path(directory) / 'journal', campaign)
            plan = build_window_plan(ExposureState('candidate', 'baseline'), 1, 'healthy')
            case = case_from_plan(plan['members'][0]['case'])
            agent = FaultInjectedCandidate('healthy')
            binding = {'namespace': 'one', 'case': case, 'agent': agent.name,
                       'reverse': False, 'manifest_digest': 'a' * 64}
            self.assertEqual(journal.inspect_many([binding])[0]['status'], 'missing')
            journal.execute(case, agent, namespace='one', manifest_digest='a' * 64)
            rows = journal.inspect_many([binding])
            self.assertEqual(rows[0]['status'], 'completed')
            rows[0]['artifact']['orders'].clear()
            self.assertTrue(journal.inspect_many([binding])[0]['artifact']['orders'])
            with self.assertRaises(ValueError):
                journal.inspect_many([{**binding, 'manifest_digest': 'b' * 64}])
