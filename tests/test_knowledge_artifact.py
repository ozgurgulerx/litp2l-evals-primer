"""Check the book's retained execution evidence, not only a generated fixture."""

import json
from pathlib import Path
import unittest

from cx_eval_lab.knowledge_action import replay_study


class RetainedKnowledgeEvidenceTests(unittest.TestCase):
    def test_published_packet_replays_and_preserves_case_denominators(self):
        path = Path(__file__).resolve().parents[1] / 'docs/assets/knowledge-action-study-v1.json'
        report = json.loads(path.read_text())
        trials = replay_study(report)
        self.assertEqual(18, len(trials))
        self.assertIs(report['deployment_authorized'], False)
        self.assertIs(report['conformance_passed'], True)
        self.assertEqual([1, 3, 3, 0, 1, 1], [row['contract_passes'] for row in report['summary']])
        self.assertEqual([3] * 6, [row['case_count'] for row in report['summary']])
        self.assertEqual([0, 0, 0, 1, 2, 2], [row['blocked_attempts'] for row in report['summary']])
        self.assertEqual([2, 0, 0, 2, 0, 0], [row['abstentions'] for row in report['summary']])


if __name__ == '__main__':
    unittest.main()
