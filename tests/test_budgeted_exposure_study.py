"""Full fixed campaign replay rejects rehashed evidence fabrication."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab import budgeted_exposure_study as study
from cx_eval_lab.evidence import canonical_hash


def rehash(packet):
    packet['report_hash'] = canonical_hash({key: value for key, value in packet.items()
                                            if key != 'report_hash'})
    return packet


class BudgetedExposureStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = study.run_study()

    def test_registered_campaign_executes_shadow_canary_and_restricted(self):
        self.assertTrue(study.verify_study(self.packet))
        self.assertTrue(self.packet['conformance_passed'])
        self.assertFalse(self.packet['deployment_authorized'])
        windows = self.packet['windows']
        self.assertEqual([row['before']['stage'] for row in windows], ['shadow', 'canary', 'restricted'])
        self.assertEqual([row['served_candidate'] for row in windows], [0, 4, 4])
        self.assertEqual([row['budget_after']['charged_actions'] for row in windows], [0, 2, 2])
        self.assertEqual([len(row['budget_after']['denials']) for row in windows], [0, 2, 6])
        self.assertEqual(windows[-1]['budget_after']['charged_cents'], {'EUR': 9000})
        self.assertEqual([row['summary']['candidate_completed'] for row in windows], [40, 2, 0])
        self.assertTrue(all(row['baseline']['passed'] for window in windows for row in window['artifacts']))

    def test_retained_packet_preserves_history_and_requires_matching_environment(self):
        raw = Path('docs/assets/budgeted-exposure-v1.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '9a43840a5df80384f40378adf359639d971b5aaece28c4c1b4087b7ac303450a')
        packet = json.loads(raw)
        inventory = study._inventory()
        if packet['source_inventory'] == inventory:
            self.assertTrue(study.verify_study(packet))
        else:
            with patch.object(study, 'execute_window') as execute, self.assertRaisesRegex(ValueError, 'source inventory'):
                study.verify_study(packet)
            execute.assert_not_called()

    def test_rehashed_semantic_mutations_fail_full_replay(self):
        mutations = (
            ('charge', lambda p: p['windows'][1]['budget_after']['charges'][0].update(amount_cents=1)),
            ('currency', lambda p: p['windows'][1]['budget_after']['charges'][0].update(currency='USD')),
            ('event', lambda p: p['windows'][1]['artifacts'][0]['baseline']['tool_events'].pop()),
            ('outcome', lambda p: p['windows'][1]['artifacts'][0]['baseline']['output'].update(claimed_outcome='needs_review')),
            ('scope', lambda p: p['windows'][1]['artifacts'][0]['effect_scopes'].update(baseline='served_candidate_campaign')),
            ('namespace', lambda p: p['windows'][1]['budget_after']['charges'][0].update(execution_namespace='different')),
            ('policy', lambda p: p['policy'].update(max_actions=3)),
            ('decision', lambda p: p['windows'][1]['decision'].update(reason='simulation_healthy_window')),
            ('observation', lambda p: p['windows'][1]['window']['observations'][0].update(candidate_pass=False)),
            ('omitted', lambda p: p['windows'][1]['artifacts'].pop()),
            ('duplicate', lambda p: p['windows'][1]['artifacts'].append(copy.deepcopy(p['windows'][1]['artifacts'][0]))),
            ('numeric_bool', lambda p: p['windows'][1].update(served_candidate=True)),
            ('integer_bool', lambda p: p.update(deployment_authorized=0)),
            ('extra_field', lambda p: p.update(extra='unregistered')),
        )
        for name, mutation in mutations:
            packet = copy.deepcopy(self.packet)
            mutation(packet)
            with self.subTest(name=name), self.assertRaises(ValueError):
                study.verify_study(rehash(packet))

    def test_source_drift_blocks_before_execution(self):
        packet = copy.deepcopy(self.packet)
        packet['source_inventory']['sources'] = {}
        with patch.object(study, 'execute_window') as execute, self.assertRaises(ValueError):
            study.verify_study(rehash(packet))
        execute.assert_not_called()
        with patch.object(study, '_inventory', return_value={}), patch.object(study, 'execute_window') as execute:
            with self.assertRaises(ValueError):
                study.verify_study(self.packet)
            execute.assert_not_called()

    def test_only_recorded_finite_nonnegative_elapsed_can_vary(self):
        packet = copy.deepcopy(self.packet)
        packet['windows'][0]['artifacts'][0]['baseline']['elapsed_ms'] = 123.0
        self.assertTrue(study.verify_study(rehash(packet)))
        for value in (True, -1, float('inf'), float('nan'), 'fast', 10**400):
            packet = copy.deepcopy(self.packet)
            packet['windows'][0]['artifacts'][0]['baseline']['elapsed_ms'] = value
            with self.subTest(value=value), patch.object(study, 'execute_window') as execute:
                with self.assertRaises(ValueError):
                    study.verify_study(rehash(packet))
                execute.assert_not_called()

    def test_unknown_nested_elapsed_field_is_not_ignored(self):
        packet = copy.deepcopy(self.packet)
        packet['windows'][0]['artifacts'][0]['baseline']['output']['elapsed_ms'] = 1
        with self.assertRaises(ValueError):
            study.verify_study(rehash(packet))

    def test_malformed_and_bad_hash_fail(self):
        for packet in (None, [], {}, {**self.packet, 'report_hash': 'invented'}):
            with self.subTest(packet=type(packet).__name__), self.assertRaises(ValueError):
                study.verify_study(packet)

    def test_cli_output_verify_and_preexecution_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'nested' / 'study.json'
            command = [sys.executable, '-m', 'cx_eval_lab.budgeted_exposure_study']
            result = subprocess.run([*command, '--output', str(output)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([*command, '--verify', str(output)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            with patch.object(sys, 'argv', ['study', '--output', str(output)]), patch.object(study, 'run_study') as run:
                with self.assertRaises(SystemExit):
                    study.main()
                run.assert_not_called()

    def test_cli_broken_symlink_output_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'symlink.json'
            output.symlink_to(Path(directory) / 'missing.json')
            with patch.object(sys, 'argv', ['study', '--output', str(output)]), patch.object(study, 'run_study') as run:
                with self.assertRaises(SystemExit):
                    study.main()
                run.assert_not_called()
