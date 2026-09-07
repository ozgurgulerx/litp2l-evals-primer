"""The budget campaign must generate and replay fresh evidence in CI."""

import unittest
from pathlib import Path

import yaml


class BudgetedWorkflowTests(unittest.TestCase):
    def test_fresh_campaign_replay_is_required_and_retained(self):
        workflow = yaml.safe_load(Path('.github/workflows/eval-conformance.yml').read_text())
        job = workflow['jobs']['conformance']
        steps = job['steps']
        matches = [step for step in steps
                   if 'cx_eval_lab.budgeted_exposure_study' in step.get('run', '')]
        self.assertEqual(1, len(matches), 'missing required budget generation/replay step')
        step = matches[0]
        self.assertNotIn('if', step)
        self.assertNotIn('continue-on-error', step)
        self.assertNotIn('continue-on-error', job)
        self.assertEqual('bash', step['shell'])
        self.assertEqual([
            'uv run python -m cx_eval_lab.budgeted_exposure_study --output ci-evidence/budgeted-exposure.json',
            'uv run python -m cx_eval_lab.budgeted_exposure_study --verify ci-evidence/budgeted-exposure.json',
        ], step['run'].strip().splitlines())
        uploads = [item for item in steps if item.get('uses', '').startswith('actions/upload-artifact@')]
        self.assertEqual(1, len(uploads))
        self.assertEqual('always()', uploads[0]['if'])
        self.assertIn('ci-evidence/', uploads[0]['with']['path'].splitlines())
        self.assertLess(steps.index(step), steps.index(uploads[0]))
