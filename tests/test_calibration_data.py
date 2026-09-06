"""Calibration receipts must be derived from retained annotation rows."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cx_eval_lab.evidence import canonical_hash
from tests.test_semantic_stage import CONFIG, FixtureJudge, NOW


def packet():
    scope = {'dataset_version': 'refund-v1', 'policy_version': 'refund-policy-v1',
             'slices': ['language:en', 'risk:standard', 'journey:refund']}
    rows = []
    for label in ('truthful', 'false'):
        for index in range(100):
            identity = f'{label}-{index}'
            rows.append({
                'id': identity, 'group_id': identity, 'split': 'calibration',
                'scope': copy.deepcopy(scope),
                'evidence': {'request': identity, 'message': 'Synthetic annotation control'},
                'reviews': [{'reviewer_id': 'reviewer-a', 'label': label},
                            {'reviewer_id': 'reviewer-b', 'label': label}],
                'adjudication': None,
                'judgment': {'verdict': 'pass' if label == 'truthful' else 'fail',
                             'evaluator_version': 'fixture-judge-v1',
                             'configuration_hash': CONFIG,
                             'criterion_id': 'refund_customer_message_truth_v1'},
            })
            rows[-1]['judgment']['evidence_hash'] = canonical_hash(rows[-1]['evidence'])
    return {'schema_version': 'calibration-annotations-v1', 'evidence_kind': 'synthetic',
            'scope': scope, 'rows': rows}


def policy():
    return dict(issued_at='2026-09-01T00:00:00+00:00',
                expires_at='2026-10-01T00:00:00+00:00', minimum_per_class=30,
                max_false_pass_upper=0.05, max_false_block_upper=0.05,
                max_abstention_rate=0.2)


def compile_data(data, **overrides):
    from cx_eval_lab.calibration_data import compile_calibration
    options = dict(policy=policy(), trusted_reviewers={'reviewer-a', 'reviewer-b', 'adjudicator'},
                   excluded_group_ids=set(), excluded_evidence_hashes=set())
    options.update(overrides)
    return compile_calibration(data, **options)


class CalibrationDataTests(unittest.TestCase):
    def test_counts_hash_and_registry_are_derived_from_rows(self):
        data = packet()
        record = compile_data(data)
        self.assertEqual(canonical_hash(data), record.label_artifact_hash)
        self.assertEqual((100, 100, 0, 0, 0), (record.truthful_examples, record.false_examples,
                         record.false_passes, record.false_blocks, record.abstentions))
        from cx_eval_lab.dataset import load_refund_cases
        case = load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json')[0]
        self.assertIsNone(record.rejection(FixtureJudge(), case, 'refund-policy-v1', NOW, True))
        self.assertEqual('synthetic_qualification_not_permitted',
                         record.rejection(FixtureJudge(), case, 'refund-policy-v1', NOW, False))

    def test_abstentions_and_error_denominators(self):
        data = packet()
        data['rows'][0]['judgment']['verdict'] = 'abstain'
        data['rows'][1]['judgment']['verdict'] = 'fail'
        data['rows'][100]['judgment']['verdict'] = 'pass'
        data['rows'][101]['judgment']['verdict'] = 'abstain'
        record = compile_data(data)
        self.assertEqual((1, 2, 2), (record.false_passes, record.false_blocks, record.abstentions))

    def test_disagreement_requires_independent_adjudication(self):
        data = packet()
        row = data['rows'][0]
        row['reviews'][1]['label'] = 'false'
        with self.assertRaisesRegex(ValueError, 'adjudication'):
            compile_data(data)
        row['adjudication'] = {'reviewer_id': 'adjudicator', 'label': 'false',
                               'reason': 'Synthetic correction against state evidence'}
        self.assertEqual(1, compile_data(data).false_passes)
        row['adjudication']['reviewer_id'] = 'reviewer-a'
        with self.assertRaises(ValueError):
            compile_data(data)

    def test_rejects_duplicate_groups_evidence_and_split_leakage(self):
        for key in ('id', 'group_id', 'evidence'):
            data = packet()
            data['rows'][1][key] = copy.deepcopy(data['rows'][0][key])
            with self.subTest(key=key), self.assertRaises(ValueError):
                compile_data(data)
        data = packet()
        with self.assertRaises(ValueError):
            compile_data(data, excluded_group_ids={'truthful-0'})
        with self.assertRaises(ValueError):
            compile_data(data, excluded_evidence_hashes={canonical_hash(data['rows'][0]['evidence'])})
        data['rows'][0]['split'] = 'sealed'
        with self.assertRaises(ValueError):
            compile_data(data)

    def test_rejects_mixed_configuration_scope_untrusted_and_invalid_rows(self):
        mutations = [
            lambda row: row['judgment'].update(configuration_hash=canonical_hash('new model')),
            lambda row: row['scope'].update(dataset_version='different'),
            lambda row: row['reviews'][0].update(reviewer_id='untrusted'),
            lambda row: row['reviews'][1].update(reviewer_id='reviewer-a'),
            lambda row: row['reviews'][0].update(label='uncertain'),
            lambda row: row['judgment'].update(verdict='maybe'),
            lambda row: row['evidence'].update(message='changed after judging'),
            lambda row: row.update(evidence={}),
            lambda row: row.update(false_passes=0),
        ]
        for mutate in mutations:
            data = packet()
            mutate(data['rows'][0])
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                compile_data(data)

    def test_rejects_aggregate_overrides_and_unknown_packet_fields(self):
        data = packet()
        with self.assertRaises(ValueError):
            compile_data(data, policy={**policy(), 'false_passes': 0})
        data['false_passes'] = 0
        with self.assertRaises(ValueError):
            compile_data(data)

    def test_rejects_malformed_policy_timestamps_without_traceback(self):
        for field in ('issued_at', 'expires_at'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_data(packet(), policy={**policy(), field: 123})

    def test_rejects_incomplete_nonfinite_and_unresolved_packets(self):
        for mutate in (
            lambda data: data.update(schema_version='unknown'),
            lambda data: data.update(rows=[]),
            lambda data: data['scope'].update(slices=[]),
            lambda data: data['scope'].update(slices=['x', 'x']),
            lambda data: data['scope'].update(dataset_version=''),
            lambda data: data['rows'][0].update(reviews=[]),
            lambda data: data['rows'][0].update(adjudication={}),
            lambda data: data['rows'][0]['evidence'].update(value=float('nan')),
        ):
            data = packet()
            mutate(data)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                compile_data(data)
        with self.assertRaises(ValueError):
            compile_data(packet(), trusted_reviewers='reviewer-a')

    def test_published_example_is_recomputable_and_not_qualified(self):
        from cx_eval_lab.calibration_data import compile_calibration
        from dataclasses import asdict
        from types import SimpleNamespace
        report = json.loads(Path('docs/assets/calibration-compiled-v1.json').read_text())
        record = compile_calibration(report['annotations'], **report['operator_config'])
        self.assertEqual(json.loads(json.dumps(asdict(record))), report['record'])
        self.assertEqual(record.content_hash, report['record_hash'])
        self.assertEqual((2, 2, 1, 1, 1), (record.truthful_examples, record.false_examples,
                         record.false_passes, record.false_blocks, record.abstentions))
        from cx_eval_lab.dataset import load_refund_cases
        case = load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json')[0]
        judge = SimpleNamespace(evaluator_version=record.evaluator_version,
                                configuration_hash=record.configuration_hash)
        self.assertEqual('insufficient_calibration_examples',
                         record.rejection(judge, case, 'refund-policy-v1', NOW, True))

    def test_cli_main_success_and_safe_error_are_instrumented(self):
        from cx_eval_lab.calibration_data import main
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / 'record.json')
            args = ['calibration', '--input', 'evals/cx-support/examples/calibration-annotations-v1.json',
                    '--config', 'evals/cx-support/examples/calibration-policy-v1.json', '--output', output]
            with patch.object(sys, 'argv', args):
                main()
                with patch('sys.stderr'), self.assertRaises(SystemExit) as raised:
                    main()
                self.assertEqual(2, raised.exception.code)

    def test_cli_retains_input_and_computed_record_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, config, output = (root / name for name in ('labels.json', 'policy.json', 'result.json'))
            source.write_text(json.dumps(packet()))
            config.write_text(json.dumps({'policy': policy(),
                'trusted_reviewers': ['reviewer-a', 'reviewer-b', 'adjudicator'],
                'excluded_group_ids': [], 'excluded_evidence_hashes': []}))
            command = [sys.executable, '-m', 'cx_eval_lab.calibration_data', '--input', str(source),
                       '--config', str(config), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            evidence = json.loads(output.read_text())
            self.assertEqual(packet(), evidence['annotations'])
            self.assertEqual(canonical_hash(packet()), evidence['record']['label_artifact_hash'])
            self.assertFalse(evidence['deployment_authorized'])
            before = output.read_bytes()
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(before, output.read_bytes())


if __name__ == '__main__':
    unittest.main()
