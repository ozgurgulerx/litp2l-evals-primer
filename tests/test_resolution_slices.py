"""Native slice diagnostics distinguish qualified failure from absent semantic evidence."""

import copy
import json
import unittest
from dataclasses import replace
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases
from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
from tests.test_resolution_semantic import NativeFixtureJudge, packet_for, setup_stage

SOURCE = Path(__file__).resolve().parents[1] / 'docs/assets/native-resolution-semantic-v1.json'


def plan_for(packet, required=()):
    return {'schema': 'resolution-slice-plan-v1', 'required_slices': list(required),
            'case_labels': {row['case_id']: ['journey:refund', 'surface:order-resolution']
                            for row in packet['baseline_trials']}}


class ResolutionSliceTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(SOURCE.read_text())
        self.trust = frozenset({self.source['calibration']['record_hash']})
        self.packet = self.source['comparisons'][0]['packet']

    def derive(self, packet=None, plan=None, trust=None):
        from cx_eval_lab.resolution_slices import derive_resolution_slice_report
        packet = self.packet if packet is None else packet
        return derive_resolution_slice_report(packet, plan_for(packet) if plan is None else plan,
            trusted_calibration_hashes=self.trust if trust is None else trust)

    def test_qualified_false_settlement_is_known_joint_regression(self):
        report = self.derive()
        self.assertEqual(8, len(report['structural']['overall']['changes']['unchanged_pass']))
        self.assertEqual(8, len(report['joint']['overall']['changes']['regressed']))
        self.assertEqual([], report['joint']['overall']['changes']['unqualified'])
        self.assertEqual(1, report['joint']['overall']['customer_count'])
        self.assertIsNone(report['joint']['overall']['comparison'])
        self.assertEqual('retrospective_exploratory', report['plan_binding'])
        self.assertFalse(report['deployment_authorized'])

    def test_v1_has_known_structure_but_no_joint_evidence(self):
        agent, cases = DescriptiveResolver(), example_cases()
        manifest = make_manifest(cases, agent.name, agent.name)
        packet = run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                      manifest=manifest).to_dict()
        report = self.derive(packet, trust=frozenset())
        self.assertEqual(8, len(report['structural']['overall']['changes']['unchanged_pass']))
        self.assertEqual(8, len(report['joint']['overall']['changes']['unqualified']))

    def test_v2_abstention_and_missing_qualification_are_unknown(self):
        for stage in (setup_stage(NativeFixtureJudge('abstain')), setup_stage(expires_at='2026-09-05T00:00:00Z')):
            packet = packet_for(stage)
            report = self.derive(packet, trust=frozenset({stage.calibration_hash}))
            self.assertEqual(8, len(report['joint']['overall']['changes']['unqualified']))
            self.assertEqual(8, len(report['structural']['overall']['changes']['unchanged_pass']))

    def test_required_plan_is_bound_before_actual_execution(self):
        agent, cases = DescriptiveResolver(), example_cases()
        plan = {'schema': 'resolution-slice-plan-v1', 'required_slices': ['journey:refund', 'missing'],
                'case_labels': {case.case_id: ['journey:refund'] for case in cases}}
        original = make_manifest(cases, agent.name, agent.name)
        manifest = replace(original, input_hashes=(*original.input_hashes, ('resolution-slice-plan', canonical_hash(plan))))
        packet = run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                      manifest=manifest).to_dict()
        report = self.derive(packet, plan, frozenset())
        self.assertEqual('manifest_bound_declared', report['plan_binding'])
        missing = next(row for row in report['joint']['slices'] if row['slice'] == 'missing')
        self.assertEqual('hold', missing['status'])
        self.assertIsNone(missing['candidate_rate'])
        changed = copy.deepcopy(plan)
        changed['case_labels'][cases[0].case_id].append('changed')
        with self.assertRaises(ValueError):
            self.derive(packet, changed, frozenset())

    def test_incomplete_duplicate_and_retrospective_required_plans_reject(self):
        for mode in ('omit', 'extra', 'duplicate', 'empty', 'required', 'unknown-field'):
            plan = plan_for(self.packet)
            case = next(iter(plan['case_labels']))
            if mode == 'omit':
                del plan['case_labels'][case]
            elif mode == 'extra':
                plan['case_labels']['extra-case'] = ['label']
            elif mode == 'duplicate':
                plan['case_labels'][case] = ['label', 'label']
            elif mode == 'empty':
                plan['case_labels'][case] = ['']
            elif mode == 'required':
                plan['required_slices'] = ['journey:refund']
            else:
                plan['score'] = 1
            with self.assertRaises(ValueError):
                self.derive(plan=plan)

    def test_no_automatic_trust_and_no_coherent_forgery(self):
        with self.assertRaises(ValueError):
            self.derive(trust=frozenset())
        for mode in ('case', 'bool-index', 'bool-pass', 'nan', 'summary'):
            packet = copy.deepcopy(self.packet)
            artifact = packet['trial_artifacts'][0]
            if mode == 'case':
                artifact['payload']['case']['request']['utterance'] = 'Changed.'
            elif mode == 'bool-index':
                artifact['payload']['identity']['trial_index'] = False
            elif mode == 'bool-pass':
                packet['baseline_trials'][0]['passed'] = 1
            elif mode == 'nan':
                artifact['payload']['elapsed_ms'] = float('nan')
            else:
                packet['candidate_trials'][0]['passed'] = True
            old = artifact['artifact_hash']
            artifact['artifact_hash'] = canonical_hash(artifact['payload'])
            for arm in ('baseline', 'candidate'):
                for row in packet[f'{arm}_trials']:
                    if row['artifact_hash'] == old:
                        row['artifact_hash'] = artifact['artifact_hash']
            with self.assertRaises(ValueError):
                self.derive(packet)
