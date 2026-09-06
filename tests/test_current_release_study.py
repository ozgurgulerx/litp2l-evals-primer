"""Orchestration tests; source double is not committed-source execution proof."""

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.source_provenance import SourceVerification


def source_check_double(manifest, *, expected_revision, expected_evaluator_version,
                        input_files, input_values, root):
    """Only map/identity validation; actual source bytes need the post-commit CLI."""
    if expected_revision != manifest.code_revision or expected_evaluator_version != manifest.evaluator_version:
        raise ValueError('fixture expected identity mismatch')
    registered = {key: value for key, value in manifest.input_hashes if not key.startswith('source:')}
    if input_files or registered != {key: canonical_hash(value) for key, value in input_values.items()}:
        raise ValueError('fixture input mapping mismatch')
    return SourceVerification(expected_revision, expected_evaluator_version, manifest.input_hashes)


class CurrentReleaseStudyTests(unittest.TestCase):
    def test_conformance_requires_the_expected_reason_not_only_outer_action(self):
        from copy import deepcopy
        from cx_eval_lab.current_release_study import run_study, _conforms
        with patch('cx_eval_lab.release_now.verify_sources', side_effect=source_check_double):
            study = run_study()
        mutations = (
            (('checks', 'campaign', 'status'), 'hold'),
            (('checks', 'base_receipt', 'comparison', 'status'), 'pass'),
            (('checks', 'chronology', 'evidence_after_decision'), True),
            (('checks', 'chronology', 'known_timestamps_checked'), 0),
            (('deployment_authorized',), True),
            (('authority_ceiling',), 'canary'),
        )
        for path, value in mutations:
            controls = deepcopy(study['assessments'])
            target = controls[0]['assessment']
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path):
                self.assertFalse(_conforms(controls, study['expected_revision']))

    def test_control_orchestration_without_claiming_unit_source_attestation(self):
        from cx_eval_lab.current_release_study import run_study
        with patch('cx_eval_lab.release_now.verify_sources', side_effect=source_check_double):
            study = run_study()
        self.assertFalse(study['deployment_authorized'])
        self.assertTrue(study['conformance_passed'])
        self.assertEqual(16, len(study['packet']['trial_artifacts']))
        self.assertEqual(16, len(study['transport']))
        self.assertEqual(4, len(study['calibration_transport']))
        self.assertEqual(4, len(study['calibration']['executions']))
        self.assertEqual('2026-09-07T00:00:00Z', study['calibration']['record']['expires_at'])
        self.assertEqual(study['expected_revision'], study['packet']['manifest']['code_revision'])
        controls = {item['name']: item['assessment'] for item in study['assessments']}
        self.assertEqual('hold', controls['current-diagnostic']['action'])
        self.assertEqual('current', controls['current-diagnostic']['checks']['replay']['calibration_status'])
        for name in ('revoked', 'expired', 'synthetic-disabled', 'wrong-revision',
                     'changed-cases', 'unqualified-prerequisites'):
            self.assertEqual('block', controls[name]['action'])
        self.assertEqual(0, controls['revoked']['checks']['replay']['failed_trials'])
        self.assertIn('current_calibration_not_current', controls['expired']['issues'])
        self.assertNotIn('manifest_not_current', controls['expired']['issues'])
        for control in controls.values():
            self.assertFalse(control['deployment_authorized'])
            self.assertEqual('none', control['authority_ceiling'])

    def test_calibration_is_recompiled_and_values_bind_setup(self):
        from cx_eval_lab.calibration_data import compile_calibration
        from cx_eval_lab.current_release_study import run_study
        from cx_eval_lab.order_resolution import example_cases
        with patch('cx_eval_lab.release_now.verify_sources', side_effect=source_check_double):
            study = run_study()
        calibration = study['calibration']
        record = compile_calibration(calibration['annotations'], **calibration['operator_config'])
        self.assertEqual(record.content_hash, calibration['record_hash'])
        self.assertEqual([asdict(case) for case in example_cases()], study['operator_values']['resolution-cases'])
        self.assertEqual('judge-campaign-policy-v1', study['operator_values']['campaign-policy']['schema'])
        self.assertEqual(study['calibration']['record']['configuration_hash'],
                         canonical_hash(study['operator_values']['judge-config']))

    def test_dirty_source_cannot_be_reported_as_verified(self):
        from cx_eval_lab.current_release_study import run_study
        with patch('cx_eval_lab.release_now.verify_sources', side_effect=ValueError('dirty source fixture')):
            study = run_study()
        self.assertFalse(study['conformance_passed'])
        self.assertTrue(all(item['assessment']['action'] == 'block' for item in study['assessments']))
        self.assertTrue(all('source_verification_failed' in item['assessment']['issues']
                            for item in study['assessments']))

    def test_manifest_accepts_explicit_revision_before_execution(self):
        from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases
        from cx_eval_lab.resolution_runner import make_manifest
        agent = DescriptiveResolver()
        manifest = make_manifest(example_cases(), agent.name, agent.name, code_revision='a' * 40)
        self.assertEqual('a' * 40, manifest.code_revision)

    def test_cli_refuses_to_overwrite_artifact_even_if_source_is_unqualified(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'current.json'
            command = [sys.executable, '-m', 'cx_eval_lab.current_release_study', '--output', str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            content = path.read_bytes()
            report = json.loads(content)
            self.assertEqual(0 if report['conformance_passed'] else 1, result.returncode, result.stderr)
            self.assertFalse(report['deployment_authorized'])
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(content, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
