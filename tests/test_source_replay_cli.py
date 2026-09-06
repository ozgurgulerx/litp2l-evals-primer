"""Strict replay binds complete cases and works in a fresh, committed checkout."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash
from tests.test_trial_replay import TrialReplayTests


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / 'evals/cx-support/datasets/regression/refund_v1.json'
POLICY = ROOT / 'evals/cx-support/policies/refund_gate_v1.json'


class SourceCaseBindingTests(unittest.TestCase):
    def test_full_cases_not_just_population_ids_are_bound(self):
        from cx_eval_lab.source_provenance import verify_packet_inputs
        packet = TrialReplayTests().packet()
        self.assertEqual(5, verify_packet_inputs(packet, dataset_path=DATASET, policy_path=POLICY))
        for field, value in (('eligible', False), ('amount_cents', 1)):
            changed = copy.deepcopy(packet)
            changed['trial_artifacts'][0]['payload']['case'][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'dataset case'):
                verify_packet_inputs(changed, dataset_path=DATASET, policy_path=POLICY)
        changed = copy.deepcopy(packet)
        changed['trial_artifacts'][0]['payload']['agent_input']['message'] = 'altered request'
        with self.assertRaisesRegex(ValueError, 'agent input'):
            verify_packet_inputs(changed, dataset_path=DATASET, policy_path=POLICY)

    def test_omitted_case_and_wrong_policy_label_reject(self):
        from cx_eval_lab.source_provenance import verify_packet_inputs
        packet = TrialReplayTests().packet()
        changed = copy.deepcopy(packet)
        case_id = changed['trial_artifacts'][0]['payload']['case']['case_id']
        changed['trial_artifacts'] = [a for a in changed['trial_artifacts']
            if a['payload']['case']['case_id'] != case_id]
        with self.assertRaisesRegex(ValueError, 'membership'):
            verify_packet_inputs(changed, dataset_path=DATASET, policy_path=POLICY)
        packet['manifest']['policy_version'] = 'not-this-policy'
        with self.assertRaisesRegex(ValueError, 'policy version'):
            verify_packet_inputs(packet, dataset_path=DATASET, policy_path=POLICY)


class SourceReplayCLITests(unittest.TestCase):
    def test_fresh_checkout_strict_replay_and_source_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            shutil.copytree(ROOT / 'cx_eval_lab', root / 'cx_eval_lab',
                            ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / 'evals', root / 'evals')
            for name in ('pyproject.toml', 'uv.lock'):
                shutil.copyfile(ROOT / name, root / name)
            def git(*args):
                return subprocess.run(['git', '-C', str(root), *args], check=True,
                                      capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            git('add', '.')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
            revision = git('rev-parse', 'HEAD')
            environment = {**os.environ, 'PYTHONPATH': str(root), 'CXLAB_CODE_REVISION': revision}
            def cli(*args):
                return subprocess.run([sys.executable, '-m', 'cx_eval_lab', *args],
                    cwd=root, env=environment, text=True, capture_output=True, timeout=30)
            packet_path = root / 'packet.json'
            created = cli('experiment', '--minimum-independent-clusters', '5',
                          '--output', str(packet_path))
            self.assertEqual(0, created.returncode, created.stderr)
            packet = json.loads(packet_path.read_text())['experiment']
            self.assertIn('source:cx_eval_lab/evaluators.py', dict(packet['manifest']['input_hashes']))
            command = ('replay', '--input', str(packet_path), '--verify-source',
                       '--expected-code-revision', revision,
                       '--expected-evaluator-version', 'refund-evaluators-v1',
                       '--trusted-packet-hash', canonical_hash(packet))
            replayed = cli(*command)
            self.assertEqual(0, replayed.returncode, replayed.stdout + replayed.stderr)
            self.assertIn('source/input consistency verified', replayed.stdout)
            self.assertIn('20 trials', replayed.stdout)
            self.assertIn('lab_only', replayed.stdout)
            rejected = cli('replay', '--input', str(packet_path), '--verify-source')
            self.assertEqual(2, rejected.returncode)
            changed = root / 'cx_eval_lab/evaluators.py'
            changed.write_text(changed.read_text() + '\n# source changed\n')
            rejected = cli(*command)
            self.assertEqual(2, rejected.returncode)
            self.assertIn('source', rejected.stdout)


if __name__ == '__main__':
    unittest.main()
