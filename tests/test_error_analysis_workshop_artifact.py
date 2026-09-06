"""Published workshop is exactly reproducible from independently selected fixture pins."""

import json
import unittest
from pathlib import Path

from cx_eval_lab.error_analysis_workshop import build_workshop

ROOT = Path(__file__).resolve().parents[1]


class ErrorAnalysisWorkshopArtifactTests(unittest.TestCase):
    def test_retained_workshop_rederives_without_executing_agents(self):
        retained = json.loads((ROOT / 'docs/assets/error-analysis-workshop-v1.json').read_text())
        actual = build_workshop(ROOT / 'docs/assets/native-resolution-semantic-v1.json',
            'sha256:638237b1615ec159c87d8ec8f2bb748867c2b319c93ff678470f4e0619419839',
            frozenset({'sha256:454a18e2f18782f37ecfb2c7832a259aead13455be9cacfe94a7464e0d54730b'}))
        self.assertEqual(retained, actual)
        self.assertFalse(actual['new_agent_executions'])
        self.assertEqual(5, actual['summary']['failed_trials'])
        self.assertEqual(3, actual['summary']['passed_trials'])
        self.assertEqual(1, actual['summary']['customer_count'])
