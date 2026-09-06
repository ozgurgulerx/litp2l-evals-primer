"""Re-grade the retained book packet; not historical process authentication."""

import json
from pathlib import Path
import unittest

from cx_eval_lab.containment_study import _conforms, grade
from cx_eval_lab.evidence import canonical_hash


class ContainmentArtifactTests(unittest.TestCase):
    def test_retained_effects_and_process_identities_support_the_published_controls(self):
        path = Path(__file__).resolve().parents[1] / 'docs/assets/containment-study-v1.json'
        report = json.loads(path.read_text())
        self.assertIs(report['deployment_authorized'], False)
        self.assertEqual(canonical_hash(report['configuration']), report['registration_hash'])
        self.assertTrue(_conforms(report['trials']))
        for trial in report['trials']:
            payload = {key: value for key, value in trial.items() if key != 'artifact_hash'}
            self.assertEqual(canonical_hash(payload), trial['artifact_hash'])
            self.assertEqual(grade(trial['final_state'], trial['configuration']['kind']), trial['grade'])
            worker_pids = {p['pid'] for p in trial['processes'] if p['role'] == 'worker'}
            self.assertEqual(1, len(worker_pids))
            for event in trial['final_state']['events']:
                if event['actor'] == 'worker':
                    self.assertIn(event['pid'], worker_pids)


if __name__ == '__main__':
    unittest.main()
