"""Citation mechanics do not replace supplied semantic review or dated truth."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ReportCitationTests(unittest.TestCase):
    def rebind_references(self, inputs):
        from cx_eval_lab.evidence import canonical_hash
        context = canonical_hash({k: v for k, v in inputs.items() if k not in ('references', 'correction_review')})
        for ref in inputs['references']:
            ref['context_hash'] = context
        inputs['references'][1]['supersedes_hash'] = canonical_hash(inputs['references'][0])
        inputs['correction_review']['previous_reference_hash'] = canonical_hash(inputs['references'][0])
        inputs['correction_review']['updated_reference_hash'] = canonical_hash(inputs['references'][1])

    def test_dimensions_have_explicit_different_denominators(self):
        from cx_eval_lab.report_citations import run_study
        report = run_study()
        metrics = report['citation_analysis']['metrics']
        self.assertEqual((3, 4), (metrics['resolved_links']['numerator'], metrics['resolved_links']['denominator']))
        self.assertEqual(.5, metrics['entailed_all_attempted_links']['rate'])
        self.assertEqual(2 / 3, metrics['entailed_resolved_links']['rate'])
        self.assertEqual(.6, metrics['claims_with_resolved_citation']['rate'])
        self.assertEqual(.4, metrics['claims_supported_by_citations']['rate'])
        self.assertEqual(.2, metrics['claims_supported_by_current_citations']['rate'])
        self.assertEqual(.8, report['original_grade']['factual_correctness']['rate'])
        self.assertEqual(.6, report['reassessed_grade']['factual_correctness']['rate'])
        self.assertEqual(['C1'], report['correction']['changed_claim_ids'])
        self.assertFalse(report['deployment_authorized'])

    def test_stale_entailment_unresolved_and_uncited_truth_remain_distinct(self):
        from cx_eval_lab.report_citations import run_study
        report = run_study()
        links = {r['citation_id']: r for r in report['citation_analysis']['links']}
        self.assertTrue(links['L1']['resolved'])
        self.assertTrue(links['L1']['entailed'])
        self.assertFalse(links['L1']['current'])
        self.assertTrue(links['L3']['resolved'])
        self.assertFalse(links['L3']['entailed'])
        self.assertFalse(links['L4']['resolved'])
        grades = {r['claim_id']: r for r in report['reassessed_grade']['claims']}
        self.assertTrue(grades['C5']['correct'])
        self.assertFalse(grades['C5']['citation_supported'])
        self.assertEqual(5, report['reassessed_grade']['required_questions']['addressed']['denominator'])
        self.assertEqual(4, report['reassessed_grade']['required_questions']['addressed']['numerator'])
        self.assertEqual(3, report['reassessed_grade']['required_questions']['correctly_answered']['numerator'])
        self.assertEqual(0, report['reassessed_grade']['required_questions']['justified_abstention']['numerator'])

    def test_report_corpus_and_original_review_are_immutable_across_reassessment(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.report_citations import example_inputs, run_study
        inputs = example_inputs()
        before = copy.deepcopy(inputs)
        report = run_study(inputs)
        self.assertEqual(before, inputs)
        self.assertEqual(inputs['references'][0], report['original_grade']['reference'])
        self.assertEqual(report['original_grade']['context_hash'], report['reassessed_grade']['context_hash'])
        self.assertEqual(canonical_hash(inputs['references'][0]), report['correction']['previous_reference_hash'])
        self.assertEqual(canonical_hash(inputs['references'][1]), report['correction']['updated_reference_hash'])

    def test_span_and_link_integrity_rejects_tampering(self):
        from cx_eval_lab.report_citations import example_inputs, run_study
        for mode in ('bool-span', 'negative', 'past-end', 'wrong-quote', 'source-quote', 'missing-claim',
                     'duplicate-source', 'foreign-source', 'scope', 'authority', 'date', 'false-current-reference'):
            inputs = example_inputs()
            if mode == 'bool-span':
                inputs['claims'][0]['span']['start'] = True
            elif mode == 'negative':
                inputs['claims'][0]['span']['start'] = -1
            elif mode == 'past-end':
                inputs['claims'][0]['span']['end'] = 100000
            elif mode == 'wrong-quote':
                inputs['claims'][0]['span']['quote'] = 'Wrong.'
            elif mode == 'source-quote':
                inputs['citations'][0]['source_span']['quote'] = 'Wrong.'
            elif mode == 'missing-claim':
                inputs['claims'].pop()
            elif mode == 'duplicate-source':
                inputs['sources'][1]['source_id'] = inputs['sources'][0]['source_id']
            elif mode == 'foreign-source':
                inputs['citations'][0]['source_id'] = 'foreign'
            elif mode == 'scope':
                inputs['sources'][0]['scope'] = 'elsewhere'
            elif mode == 'authority':
                inputs['references'][1]['authority'] = 'unreviewed'
            elif mode == 'date':
                inputs['sources'][0]['effective_from'] = 'not-a-date'
            else:
                inputs['references'][1]['judgments'][0]['source_id'] = 'policy-old'
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                run_study(inputs)

    def test_replay_rejects_coherent_computed_changes(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.report_citations import replay_study, run_study
        report = run_study()
        self.assertEqual(report, replay_study(report))
        for field in ('original_grade', 'reassessed_grade', 'citation_analysis'):
            changed = copy.deepcopy(report)
            changed[field] = {}
            changed['report_hash'] = canonical_hash({k: v for k, v in changed.items() if k != 'report_hash'})
            with self.assertRaises(ValueError):
                replay_study(changed)

    def test_cli_output_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            cmd = [sys.executable, '-m', 'cx_eval_lab.report_citations', '--output', str(path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            before = path.read_bytes()
            self.assertEqual('report-citations-v1', json.loads(before)['schema'])
            self.assertNotEqual(0, subprocess.run(cmd, capture_output=True, check=False).returncode)
            self.assertEqual(before, path.read_bytes())

    def test_unapproved_second_truth_change_cannot_hide_in_reassessment(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.report_citations import example_inputs, run_study
        inputs = example_inputs()
        inputs['references'][1]['judgments'][1]['correct'] = False
        if 'correction_review' in inputs:
            inputs['correction_review']['updated_reference_hash'] = canonical_hash(inputs['references'][1])
        with self.assertRaises(ValueError):
            run_study(inputs)

    def test_retained_artifact_exact_reassessment(self):
        from cx_eval_lab.report_citations import replay_study, run_study
        path = Path(__file__).resolve().parents[1] / 'docs/assets/report-citations-v1.json'
        artifact = json.loads(path.read_text())
        self.assertEqual(run_study(), artifact)
        self.assertEqual(artifact, replay_study(artifact))

    def test_literal_unresolved_citation_cannot_be_dropped_from_denominator(self):
        from cx_eval_lab.report_citations import example_inputs, run_study
        inputs = example_inputs()
        inputs['citations'] = [c for c in inputs['citations'] if c['citation_id'] != 'L4']
        inputs['link_adjudications'] = [c for c in inputs['link_adjudications'] if c['citation_id'] != 'L4']
        self.rebind_references(inputs)
        self.assertIn('[L4]', inputs['report']['text'])
        with self.assertRaises(ValueError):
            run_study(inputs)

    def test_repeated_source_citation_does_not_inflate_supported_claim_count(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.report_citations import example_inputs, run_study
        inputs = example_inputs()
        text = inputs['report']['text'].replace('[L1]', '[L1] [L5]')
        inputs['report']['text'] = text
        for section in inputs['report']['sections']:
            quote = section['span']['quote'].replace('[L1]', '[L1] [L5]')
            start = text.index(quote)
            section['span'] = {'start': start, 'end': start + len(quote), 'quote': quote}
        for claim in inputs['claims']:
            quote = claim['span']['quote']
            start = text.index(quote)
            claim['span'] = {'start': start, 'end': start + len(quote), 'quote': quote}
        inputs['citations'].append({**copy.deepcopy(inputs['citations'][0]), 'citation_id': 'L5'})
        sources = {s['source_id']: s for s in inputs['sources']}
        claims = {c['claim_id']: c for c in inputs['claims']}
        adjudications = []
        old = {a['citation_id']: a for a in inputs['link_adjudications']}
        for citation in inputs['citations']:
            quote = '[' + citation['citation_id'] + ']'
            start = text.index(quote)
            citation['locator_span'] = {'start': start, 'end': start + len(quote), 'quote': quote}
            previous = old['L1' if citation['citation_id'] == 'L5' else citation['citation_id']]
            adjudications.append({**previous, 'citation_id': citation['citation_id'],
                'binding_hash': canonical_hash({'claim': claims[citation['claim_id']], 'citation': citation,
                                                'source': sources.get(citation['source_id'])})})
        inputs['link_adjudications'] = adjudications
        for ref in inputs['references']:
            for judgment in ref['judgments']:
                judgment['claim_binding_hash'] = canonical_hash(claims[judgment['claim_id']])
        self.rebind_references(inputs)
        analysis = run_study(inputs)['citation_analysis']
        self.assertEqual(3, analysis['metrics']['entailed_all_attempted_links']['numerator'])
        self.assertEqual(5, analysis['metrics']['entailed_all_attempted_links']['denominator'])
        self.assertEqual(2, analysis['metrics']['claims_supported_by_citations']['numerator'])
        self.assertEqual(2, analysis['unique_resolved_source_count'])

    def test_unknown_truth_and_unresolved_support_cannot_be_coerced(self):
        from cx_eval_lab.report_citations import example_inputs, run_study
        for mode in ('unknown-truth', 'unresolved-entailed', 'unresolved-quote', 'empty-span', 'reversed-span'):
            inputs = example_inputs()
            if mode == 'unknown-truth':
                inputs['references'][0]['judgments'][0]['correct'] = None
            elif mode == 'unresolved-entailed':
                inputs['link_adjudications'][3]['entailed'] = True
            elif mode == 'unresolved-quote':
                inputs['citations'][3]['source_span'] = {'start': 0, 'end': 1, 'quote': 'x'}
            else:
                span = inputs['claims'][0]['span']
                span['end'] = span['start'] - (mode == 'reversed-span')
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                run_study(inputs)
