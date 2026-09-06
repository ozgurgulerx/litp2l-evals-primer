"""Executed ranking/packing interventions retain facts, byte counts and backend outcomes."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ContextPackingTests(unittest.TestCase):
    def study(self, inputs=None):
        from cx_eval_lab.context_packing import run_study
        return run_study(inputs)

    def test_more_retrieved_evidence_can_leave_less_packed_evidence(self):
        report = self.study()
        rows = {row['arm']: row for row in report['summary'] if row['agent'] == 'policy-control'}
        for arm, retrieved, packed, passes in (('top2', 0.5, 0.5, 0), ('top5', 1, 0, 0),
                                               ('filtered-top5', 1, 1, 3), ('oracle', 1, 1, 3)):
            row = rows[arm]
            self.assertEqual(retrieved, row['retrieved_evidence_unit_recall'])
            self.assertEqual(packed, row['packed_evidence_unit_recall'])
            self.assertEqual(passes, row['contract_passes'])
        self.assertEqual(24, len(report['trials']))
        self.assertFalse(report['deployment_authorized'])

    def test_actual_utf8_serialized_context_obeys_one_budget_in_all_arms(self):
        report = self.study()
        for trial in report['trials']:
            p = trial['payload']
            self.assertEqual(len(p['agent_input']['context_body'].encode('utf-8')), p['packed_bytes'])
            self.assertLessEqual(p['packed_bytes'], report['inputs']['budget_bytes'])
            self.assertEqual([], p['initial_state']['refunds'])
            self.assertEqual({'request', 'context_body'}, set(p['agent_input']))
            for passage in json.loads(p['agent_input']['context_body']):
                self.assertEqual({'text', 'facts'}, set(passage))
        top5 = next(t['payload'] for t in report['trials'] if t['payload']['arm'] == 'top5')
        self.assertEqual(['promo'], top5['packed_ids'])
        self.assertTrue(any(row['decision'] == 'drop_budget' for row in top5['packing_events']))

    def test_duplicate_passage_does_not_duplicate_evidence_units(self):
        report = self.study()
        top2 = next(t['payload'] for t in report['trials'] if t['payload']['arm'] == 'top2')
        self.assertEqual(2, len(top2['selected_ids']))
        self.assertEqual(['window_days'], top2['grade']['retrieved_units'])
        filtered = next(t['payload'] for t in report['trials'] if t['payload']['arm'] == 'filtered-top5')
        self.assertEqual({'drop_version', 'drop_source_kind', 'drop_duplicate'},
                         {row['decision'] for row in filtered['selection_events'] if row['decision'] != 'keep'})

    def test_oracle_cannot_repair_an_agent_that_ignores_amount_limit(self):
        report = self.study()
        mutant = next(row for row in report['summary'] if row['agent'] == 'ignore-limit-mutant' and row['arm'] == 'oracle')
        self.assertEqual(2, mutant['contract_passes'])
        self.assertEqual(1, mutant['blocked_attempts'])
        row = next(t['payload'] for t in report['trials']
                   if t['payload']['agent'] == 'ignore-limit-mutant' and t['payload']['arm'] == 'oracle'
                   and t['payload']['case_id'] == 'over-limit')
        self.assertEqual('refund', row['decision']['action'])
        self.assertEqual('amount_limit', row['tool_events'][0]['result']['reason'])
        self.assertEqual([], row['final_state']['refunds'])
        self.assertFalse(row['grade']['contract_passed'])

    def test_agent_abstains_on_missing_or_conflicting_structured_facts(self):
        from cx_eval_lab.context_packing import decide
        request = {'age_days': 10, 'amount_cents': 4000}
        for facts in ([{'window_days': 30}], [{'window_days': 30, 'max_refund_cents': 5000}, {'window_days': 90}]):
            context = json.dumps([{'text': 'fixture', 'facts': row} for row in facts])
            self.assertEqual('abstain', decide({'request': request, 'context_body': context}, 'policy-control')['action'])

    def test_strict_inputs_reject_bools_nonfinite_ids_incomplete_and_conflicting_current_policy(self):
        from cx_eval_lab.context_packing import example_inputs
        for mode in ('bool', 'nan', 'duplicate-id', 'incomplete', 'conflict', 'policy-bool', 'unknown-field'):
            inputs = example_inputs()
            if mode == 'bool':
                inputs['cases'][0]['amount_cents'] = True
            elif mode == 'nan':
                inputs['budget_bytes'] = float('nan')
            elif mode == 'duplicate-id':
                inputs['passages'][1]['passage_id'] = inputs['passages'][0]['passage_id']
            elif mode == 'incomplete':
                inputs['passages'] = [p for p in inputs['passages'] if p['passage_id'] != 'limit']
            elif mode == 'conflict':
                inputs['passages'][0]['content']['facts']['window_days'] = 90
            elif mode == 'policy-bool':
                inputs['policy']['window_days'] = True
            else:
                inputs['cases'][0]['expected_pass'] = True
            with self.assertRaises(ValueError):
                self.study(inputs)

    def test_replay_reexecutes_and_rejects_coherent_grade_or_trace_changes(self):
        from cx_eval_lab.context_packing import replay_study
        from cx_eval_lab.evidence import canonical_hash
        report = self.study()
        self.assertEqual(24, len(replay_study(report)))
        for field in ('grade', 'packed_ids'):
            changed = copy.deepcopy(report)
            p = changed['trials'][0]['payload']
            if field == 'grade':
                p['grade']['contract_passed'] = True
            else:
                p['packed_ids'] = ['limit']
            changed['trials'][0]['artifact_hash'] = canonical_hash(p)
            changed['report_hash'] = canonical_hash({k: v for k, v in changed.items() if k != 'report_hash'})
            with self.assertRaises(ValueError):
                replay_study(changed)

    def test_input_is_not_mutated_and_filter_does_not_depend_on_gold_ids(self):
        from cx_eval_lab.context_packing import example_inputs
        inputs = example_inputs()
        before = copy.deepcopy(inputs)
        first = self.study(inputs)
        self.assertEqual(before, inputs)
        renamed = copy.deepcopy(inputs)
        for i, row in enumerate(renamed['passages']):
            row['passage_id'] = f'opaque-{i}'
        second = self.study(renamed)
        self.assertEqual(first['summary'], second['summary'])

    def test_cli_runs_study_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packing.json'
            cmd = [sys.executable, '-m', 'cx_eval_lab.context_packing', '--output', str(path)]
            first = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            data = path.read_bytes()
            self.assertEqual(self.study(), json.loads(data))
            self.assertNotEqual(0, subprocess.run(cmd, capture_output=True, check=False).returncode)
            self.assertEqual(data, path.read_bytes())
