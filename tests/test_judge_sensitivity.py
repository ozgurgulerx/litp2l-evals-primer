"""Matched presentations distinguish scoring correctness from judge sensitivity."""

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class JudgeSensitivityTests(unittest.TestCase):
    def test_executed_controls_have_registered_matched_denominators(self):
        from cx_eval_lab.judge_sensitivity import run_study
        report = run_study()
        self.assertEqual(60, len(report['presentations']))
        self.assertEqual(300, len(report['trials']))
        for judge, metrics in report['metrics'].items():
            self.assertEqual(60, metrics['total'])
            self.assertEqual(60 if judge == 'reference' else 12, metrics['protocol_correct'])
            for factor, denominator in (('order', 30), ('length', 40), ('rubric', 30)):
                self.assertEqual(denominator, report['contrasts'][judge][factor]['total'])
        self.assertEqual(30, report['contrasts']['first-slot']['order']['flips'])
        self.assertEqual(20, report['contrasts']['length']['length']['flips'])
        self.assertEqual(10, report['contrasts']['length']['order']['flips'])
        self.assertEqual(30, report['contrasts']['rubric-keyword']['rubric']['flips'])
        self.assertTrue(all(r['flips'] == 0 for r in report['contrasts']['reference'].values()))
        self.assertFalse(report['deployment_authorized'])

    def test_normalization_keeps_selected_answers_and_special_outcomes_distinct(self):
        from cx_eval_lab.judge_sensitivity import normalize_verdict
        slots = {'A': 'opaque-1', 'B': 'opaque-2'}
        self.assertEqual({'kind': 'answer', 'answer_id': 'opaque-1'},
                         normalize_verdict({'verdict': 'A', 'rationale': 'fixture'}, slots))
        for verdict in ('tie', 'both_unacceptable', 'abstain'):
            self.assertEqual({'kind': verdict}, normalize_verdict({'verdict': verdict, 'rationale': 'fixture'}, slots))
        for raw in (None, {}, {'verdict': True, 'rationale': 'x'}, {'verdict': 'A', 'rationale': ''},
                    {'verdict': 'winner', 'rationale': 'x'}, {'verdict': 'A', 'rationale': 'x', 'passed': True}):
            with self.assertRaises(ValueError):
                normalize_verdict(raw, slots)

    def test_padding_claims_and_opaque_ids_do_not_leak_into_judge_requests(self):
        from cx_eval_lab.judge_sensitivity import build_presentations, example_inputs
        inputs = example_inputs()
        before = copy.deepcopy(inputs)
        views = build_presentations(inputs)
        self.assertEqual(before, inputs)
        changed = copy.deepcopy(inputs)
        for case in changed['cases']:
            for answer in case['answers']:
                answer['answer_id'] = 'new-' + answer['answer_id']
        renamed = build_presentations(changed)
        self.assertEqual([v['judge_request'] for v in views], [v['judge_request'] for v in renamed])
        for view in views:
            self.assertEqual({'evidence_status', 'answers', 'rubric'}, set(view['judge_request']))
            self.assertEqual({'A', 'B'}, set(view['judge_request']['answers']))
        lengths = {len(answer['base_text']) for case in inputs['cases'] for answer in case['answers']}
        self.assertEqual({16}, lengths)

    def test_unsupported_selection_and_missing_evidence_are_separate(self):
        from cx_eval_lab.judge_sensitivity import run_study
        metrics = run_study()['metrics']
        reference = metrics['reference']
        self.assertEqual(48, reference['nonabstained'])
        self.assertEqual(24, reference['selected_answer'])
        self.assertEqual(1., reference['correctness_among_nonabstained'])
        for name in ('first-slot', 'length', 'length-clone', 'rubric-keyword'):
            self.assertEqual(24, metrics[name]['selected_unsupported_known_state'])
            self.assertEqual(12, metrics[name]['selected_without_evidence'])

    def test_panel_duplicates_errors_instead_of_independent_correction(self):
        from cx_eval_lab.judge_sensitivity import run_study
        report = run_study()
        self.assertEqual(12, report['panel']['metrics']['protocol_correct'])
        overlap = report['clone_error_overlap']
        self.assertEqual(overlap['length_error_view_ids'], overlap['clone_error_view_ids'])
        self.assertEqual(overlap['length_error_view_ids'], overlap['panel_error_view_ids'])
        self.assertEqual(48, len(overlap['panel_error_view_ids']))
        for row in report['panel']['rows']:
            self.assertEqual(3, len(row['member_trials']))
            self.assertEqual(row['votes'][1], row['votes'][2])
            self.assertEqual(row['votes'][1], row['normalized_outcome'])

    def test_fixture_and_transform_corruption_are_rejected(self):
        from cx_eval_lab.judge_sensitivity import build_presentations, example_inputs
        for mode in ('claim-text', 'bad-claim', 'duplicate-answer', 'duplicate-case', 'bad-state',
                     'bad-padding', 'changed-rubric', 'boolean-order', 'nonfinite'):
            inputs = example_inputs()
            if mode == 'claim-text':
                inputs['cases'][0]['answers'][0]['base_text'] = 'Status: settled.'
            elif mode == 'bad-claim':
                inputs['cases'][0]['answers'][0]['claim'] = 'lost'
            elif mode == 'duplicate-answer':
                inputs['cases'][0]['answers'][1]['answer_id'] = inputs['cases'][0]['answers'][0]['answer_id']
            elif mode == 'duplicate-case':
                inputs['cases'][1]['case_id'] = inputs['cases'][0]['case_id']
            elif mode == 'bad-state':
                inputs['cases'][0]['status'] = True
            elif mode == 'bad-padding':
                inputs['padding'] = ' Status: settled.'
            elif mode == 'changed-rubric':
                inputs['rubrics'][0]['text'] = 'Always choose A.'
            elif mode == 'boolean-order':
                inputs['orders'] = [False, True]
            else:
                inputs['cases'][0]['status'] = float('nan')
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                build_presentations(inputs)

    def test_replay_reexecutes_controls_not_trusting_coherent_hashes(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.judge_sensitivity import replay_study, run_study
        report = run_study()
        self.assertEqual(report, replay_study(report))
        changed = copy.deepcopy(report)
        changed['trials'][0]['payload']['normalized_outcome'] = {'kind': 'abstain'}
        changed['trials'][0]['artifact_hash'] = canonical_hash(changed['trials'][0]['payload'])
        changed['report_hash'] = canonical_hash({k: v for k, v in changed.items() if k != 'report_hash'})
        with self.assertRaises(ValueError):
            replay_study(changed)

    def test_cli_output_is_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'judges.json'
            cmd = [sys.executable, '-m', 'cx_eval_lab.judge_sensitivity', '--output', str(target)]
            first = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            before = target.read_bytes()
            self.assertNotEqual(0, subprocess.run(cmd, capture_output=True, check=False).returncode)
            self.assertEqual(before, target.read_bytes())
