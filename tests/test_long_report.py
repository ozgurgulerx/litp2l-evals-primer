"""Gold inventories stay independent of text-only extraction controls."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class LongReportTests(unittest.TestCase):
    def test_controls_execute_on_actual_text_without_gold_flags(self):
        from cx_eval_lab.long_report import extract_claims
        text = '# Brief\n\nContext is not a finding.\n\nFinding: Alpha applies [L1]; Beta does not apply.\n'
        sentence = extract_claims(text, 'sentence')
        clauses = extract_claims(text, 'clause')
        cited = extract_claims(text, 'cited-only')
        self.assertEqual(1, len(sentence))
        self.assertEqual(['Alpha applies', 'Beta does not apply'], [u['span']['quote'] for u in clauses])
        self.assertEqual(['Alpha applies'], [u['span']['quote'] for u in cited])
        self.assertEqual(['L1'], cited[0]['citation_ids'])
        for unit in sentence + clauses + cited:
            span = unit['span']
            self.assertEqual(span['quote'], text[span['start']:span['end']])

    def test_full_reports_and_shared_task_corpus_rubric_are_retained(self):
        from cx_eval_lab.long_report import run_study
        report = run_study()
        self.assertEqual(2, len(report['reports']))
        for row in report['reports']:
            self.assertGreaterEqual(row['word_count'], 700)
            self.assertGreaterEqual(row['gold_claim_count'], 12)
            self.assertEqual(1., row['controls']['clause']['atomic_recall']['rate'])
            self.assertLess(row['controls']['sentence']['atomic_recall']['rate'], 1.)
            self.assertEqual(row['shared_context_hash'], report['shared_context_hash'])
        self.assertFalse(report['deployment_authorized'])

    def test_omitting_uncited_claims_cannot_hide_the_fixed_denominator(self):
        from cx_eval_lab.long_report import run_study
        original = run_study()['reports'][0]
        full, omitted = original['controls']['clause'], original['controls']['cited-only']
        self.assertLess(omitted['atomic_recall']['rate'], 1.)
        self.assertGreater(omitted['observed_support']['rate'], full['observed_support']['rate'])
        self.assertEqual(full['full_inventory_support'], omitted['full_inventory_support'])
        self.assertTrue(omitted['omitted_claim_ids'])
        self.assertEqual(original['gold_claim_count'], omitted['atomic_recall']['denominator'])

    def test_extraction_receives_text_only_and_no_expected_labels(self):
        from cx_eval_lab.long_report import extract_claims, run_study
        with patch('cx_eval_lab.long_report.extract_claims', wraps=extract_claims) as spy:
            run_study()
        self.assertGreaterEqual(spy.call_count, 6)
        for call in spy.call_args_list:
            self.assertIsInstance(call.args[0], str)
            self.assertIsInstance(call.args[1], str)
            self.assertEqual(2, len(call.args))

    def test_invalid_spans_source_dates_and_marker_omissions_rejected(self):
        from cx_eval_lab.long_report import example_inputs, run_study
        for mode in ('bool-span', 'quote', 'missing-claim', 'duplicate-claim', 'source-date', 'unknown-truth', 'drop-link'):
            inputs = example_inputs()
            claim = inputs['reports'][0]['claims'][0]
            if mode == 'bool-span':
                claim['span']['start'] = True
            elif mode == 'quote':
                claim['span']['quote'] = 'Different text'
            elif mode == 'missing-claim':
                inputs['reports'][0]['claims'].pop()
            elif mode == 'duplicate-claim':
                inputs['reports'][0]['claims'][1]['claim_id'] = claim['claim_id']
            elif mode == 'source-date':
                inputs['sources'][0]['effective_from'] = 'not-date'
            elif mode == 'unknown-truth':
                claim['status'] = None
            else:
                claim['links'].clear()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                run_study(inputs)

    def test_replay_rejects_coherently_rehashed_omission_scores(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.long_report import replay_study, run_study
        report = run_study()
        self.assertEqual(report, replay_study(report))
        changed = copy.deepcopy(report)
        changed['reports'][0]['controls']['cited-only']['atomic_recall']['rate'] = 1.
        changed['report_hash'] = canonical_hash({k: v for k, v in changed.items() if k != 'report_hash'})
        with self.assertRaises(ValueError):
            replay_study(changed)

    def test_cli_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'long.json'
            cmd = [sys.executable, '-m', 'cx_eval_lab.long_report', '--output', str(target)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            before = target.read_bytes()
            self.assertEqual('long-report-study-v1', json.loads(before)['schema'])
            self.assertNotEqual(0, subprocess.run(cmd, capture_output=True, check=False).returncode)
            self.assertEqual(before, target.read_bytes())

    def test_duplicate_empty_and_whole_report_predictions_do_not_earn_atomic_credit(self):
        from cx_eval_lab.long_report import score_extraction
        text = 'Finding: Alpha applies [L1]; Beta fails.\n'
        claims = [{'claim_id': 'A', 'span': {'start': 9, 'end': 22, 'quote': 'Alpha applies'}, 'status': 'supported'},
                  {'claim_id': 'B', 'span': {'start': 29, 'end': 39, 'quote': 'Beta fails'}, 'status': 'unsupported'}]
        # Author the exact Beta span separately from the extraction function.
        claims[1]['span']['start'] = text.index('Beta fails')
        claims[1]['span']['end'] = text.index('Beta fails') + len('Beta fails')
        report = {'text': text, 'claims': claims}
        prediction = {'unit_id': 'p1', 'span': dict(claims[0]['span']), 'citation_ids': ['L1']}
        duplicate = {**copy.deepcopy(prediction), 'unit_id': 'p2'}
        scored = score_extraction([prediction, duplicate], report)
        self.assertEqual(2, scored['extracted_unit_count'])
        self.assertEqual(.5, scored['atomic_recall']['rate'])
        self.assertEqual(.5, scored['exact_unit_precision']['rate'])
        self.assertEqual('p1', scored['units'][1]['duplicate_of'])
        empty = score_extraction([], report)
        self.assertEqual(0., empty['atomic_recall']['rate'])
        self.assertIsNone(empty['observed_support']['rate'])
        whole = score_extraction([{'unit_id': 'all', 'span': {'start': 0, 'end': len(text), 'quote': text},
                                  'citation_ids': ['L1']}], report)
        self.assertEqual(0., whole['atomic_recall']['rate'])
        self.assertEqual(['A', 'B'], whole['units'][0]['contained_claim_ids'])
        self.assertIsNone(whole['observed_support']['rate'])

    def test_supported_epistemic_statement_is_not_an_unknown_assertion(self):
        from cx_eval_lab.long_report import example_inputs, run_study
        inputs = example_inputs()
        original = {c['claim_id']: c for c in inputs['reports'][0]['claims']}
        repaired = {c['claim_id']: c for c in inputs['reports'][1]['claims']}
        self.assertEqual('supported', original['C08']['status'])
        self.assertEqual('unknown', original['C08']['answerability'])
        self.assertEqual('supported', repaired['C16']['status'])
        self.assertEqual('unknown', repaired['C16']['answerability'])
        report = run_study(inputs)
        self.assertEqual(0, report['reports'][1]['gold_status_counts']['unknown'])
        self.assertEqual(4, report['reports'][1]['underlying_unknown_count'])
        self.assertEqual(20, report['reports'][1]['gold_status_counts']['supported'])

    def test_nested_gold_atoms_and_missing_synthesis_obligations_rejected(self):
        from cx_eval_lab.long_report import example_inputs, run_study
        inputs = example_inputs()
        nested = copy.deepcopy(inputs['reports'][0]['claims'][0])
        nested['claim_id'] = 'nested'
        nested['links'] = []
        nested['span']['end'] = nested['span']['start'] + len('Request R17')
        nested['span']['quote'] = inputs['reports'][0]['text'][nested['span']['start']:nested['span']['end']]
        inputs['reports'][0]['claims'].append(nested)
        for row in inputs['reports'][0]['coverage']:
            if row['question_id'] in nested['question_ids']:
                row['claim_ids'].append('nested')
        with self.assertRaises(ValueError):
            run_study(inputs)
        inputs = example_inputs()
        inputs['reports'][0]['synthesis'] = []
        with self.assertRaises(ValueError):
            run_study(inputs)
