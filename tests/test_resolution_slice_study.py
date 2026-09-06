"""Retrospective native diagnostics require explicit source and calibration anchors."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path('docs/assets/native-resolution-semantic-v1.json')
DIGEST = 'sha256:638237b1615ec159c87d8ec8f2bb748867c2b319c93ff678470f4e0619419839'
TRUST = 'sha256:454a18e2f18782f37ecfb2c7832a259aead13455be9cacfe94a7464e0d54730b'


class ResolutionSliceStudyTests(unittest.TestCase):
    def derive(self, path=SOURCE, digest=DIGEST, trust=frozenset({TRUST})):
        from cx_eval_lab.resolution_slice_study import derive_study
        return derive_study(path, expected_source_sha256=digest, trusted_calibration_hashes=trust)

    def test_retrospective_three_comparisons_preserve_source(self):
        before = SOURCE.read_bytes()
        report = self.derive()
        self.assertEqual(3, len(report['comparisons']))
        self.assertEqual(DIGEST, report['source']['bytes_sha256'])
        self.assertFalse(report['new_agent_executions'])
        self.assertFalse(report['deployment_authorized'])
        for comparison in report['comparisons']:
            self.assertNotIn('packet', comparison)
            self.assertEqual([], comparison['plan']['required_slices'])
        self.assertEqual(before, SOURCE.read_bytes())

    def test_retained_report_rederives_exactly(self):
        retained = json.loads(Path('docs/assets/resolution-slices-v1.json').read_bytes())
        self.assertEqual(retained, self.derive())

    def test_missing_or_wrong_explicit_anchors_fail(self):
        for digest, trust in ((DIGEST, frozenset()), (DIGEST, frozenset({'sha256:' + '0'*64})),
                              ('sha256:' + '0'*64, frozenset({TRUST}))):
            with self.assertRaises(ValueError):
                self.derive(digest=digest, trust=trust)

    def test_reanchored_nonsynthetic_and_forged_calibration_fail(self):
        for mutation in ('kind', 'record', 'nan'):
            data = json.loads(SOURCE.read_bytes())
            if mutation == 'kind':
                data['evidence_kind'] = 'measured'
            elif mutation == 'record':
                data['calibration']['record']['dataset_version'] = 'forged'
            else:
                data['unexpected'] = float('nan')
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / SOURCE.name
                path.write_text(json.dumps(data))
                digest = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    self.derive(path, digest)

    def test_changed_bytes_fail_against_original_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / SOURCE.name
            path.write_bytes(SOURCE.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'source byte hash'):
                self.derive(path)

    def test_cli_requires_explicit_trust_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            command = [sys.executable, '-m', 'cx_eval_lab.resolution_slice_study',
                       '--source', str(SOURCE), '--expected-source-sha256', DIGEST, '--output', str(path)]
            self.assertNotEqual(0, subprocess.run(command, capture_output=True, check=False).returncode)
            command += ['--trusted-calibration-hash', TRUST]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            before = path.read_bytes()
            self.assertEqual(self.derive(), json.loads(before))
            self.assertNotEqual(0, subprocess.run(command, capture_output=True, check=False).returncode)
            self.assertEqual(before, path.read_bytes())

    def test_inprocess_cli_and_malformed_source(self):
        from cx_eval_lab.resolution_slice_study import main
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            argv = ['study', '--source', str(SOURCE), '--expected-source-sha256', DIGEST,
                    '--trusted-calibration-hash', TRUST, '--output', str(path)]
            with patch.object(sys, 'argv', argv):
                main()
                with self.assertRaises(SystemExit):
                    main()
            broken = Path(directory) / 'broken.json'
            broken.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'malformed retained'):
                self.derive(broken, 'sha256:' + hashlib.sha256(broken.read_bytes()).hexdigest())
