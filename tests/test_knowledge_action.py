"""Local retrieval/action controls; no model or empirical transfer claims."""

import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cx_eval_lab.evidence import canonical_hash


class KnowledgeActionTests(unittest.TestCase):
    def test_retrieval_repair_and_persistent_action_failure(self):
        from cx_eval_lab.knowledge_action import run_study, replay_study
        report = run_study()
        self.assertTrue(report['conformance_passed'])
        self.assertFalse(report['deployment_authorized'])
        self.assertEqual(18, len(report['trials']))
        self.assertEqual(18, len(replay_study(report)))
        scores = {(row['arm'], row['agent']): row for row in report['summary']}
        self.assertEqual([1, 3, 3], [scores[(arm, 'policy-control')]['contract_passes']
                                   for arm in ('retrieval', 'oracle', 'full-context')])
        self.assertEqual([0, 1, 1], [scores[(arm, 'wrong-amount-mutant')]['contract_passes']
                                   for arm in ('retrieval', 'oracle', 'full-context')])
        self.assertTrue(all(row['case_count'] == 3 for row in report['summary']))

    def test_stale_retrieval_abstains_and_oracle_denial_completes(self):
        from cx_eval_lab.knowledge_action import execute_trial, example_cases, example_documents
        case, docs = example_cases()[1], example_documents()
        retrieved = execute_trial(case, docs, 'retrieval', 'policy-control')['payload']
        self.assertFalse(retrieved['grade']['knowledge_available'])
        self.assertEqual('abstain', retrieved['decision']['action'])
        self.assertEqual([], retrieved['tool_events'])
        self.assertFalse(retrieved['grade']['contract_passed'])
        oracle = execute_trial(case, docs, 'oracle', 'policy-control')['payload']
        self.assertEqual('deny', oracle['decision']['action'])
        self.assertEqual([], oracle['tool_events'])
        self.assertTrue(oracle['grade']['contract_passed'])

    def test_wrong_amount_is_attempted_then_blocked_and_state_resets(self):
        from cx_eval_lab.knowledge_action import execute_trial, example_cases, example_documents
        case, docs = example_cases()[2], example_documents()
        bad = execute_trial(case, docs, 'oracle', 'wrong-amount-mutant')['payload']
        self.assertTrue(bad['grade']['knowledge_available'])
        self.assertTrue(bad['grade']['decision_correct'])
        self.assertEqual(case.amount_cents + 1, bad['tool_events'][0]['arguments']['amount_cents'])
        self.assertEqual('blocked', bad['tool_events'][0]['result']['status'])
        self.assertEqual([], bad['final_state']['refunds'])
        self.assertFalse(bad['grade']['action_arguments_correct'])
        self.assertFalse(bad['grade']['contract_passed'])
        first = execute_trial(case, docs, 'oracle', 'policy-control')
        second = execute_trial(case, docs, 'oracle', 'policy-control')
        self.assertEqual(first, second)
        self.assertEqual(1, len(first['payload']['final_state']['refunds']))

    def test_full_context_order_reversal_does_not_change_decision_or_effects(self):
        from cx_eval_lab.knowledge_action import execute_trial, example_cases, example_documents
        for case in example_cases():
            normal = execute_trial(case, example_documents(), 'full-context', 'policy-control')['payload']
            reverse = execute_trial(case, tuple(reversed(example_documents())),
                                    'full-context', 'policy-control')['payload']
            for key in ('decision', 'tool_events', 'final_state', 'grade'):
                self.assertEqual(normal[key], reverse[key])
            self.assertNotIn('required_document_id', json.dumps(normal['agent_input']))
            self.assertNotIn('expected_action', json.dumps(normal['agent_input']))

    def test_replay_rejects_rehashed_execution_and_summary_tampering(self):
        from cx_eval_lab.knowledge_action import run_study, replay_study
        original = run_study()
        for kind in ('event', 'summary', 'decision', 'context'):
            report = copy.deepcopy(original)
            trial = next(t for t in report['trials'] if t['payload']['tool_events'])
            if kind == 'event':
                trial['payload']['tool_events'][0]['result']['status'] = 'forged'
            elif kind == 'decision':
                trial['payload']['decision']['action'] = 'deny'
            elif kind == 'context':
                trial['payload']['agent_input']['documents'] = []
            else:
                report['summary'][0]['contract_passes'] = 3
            trial['artifact_hash'] = canonical_hash(trial['payload'])
            report['study_hash'] = canonical_hash({key: value for key, value in report.items()
                                                   if key != 'study_hash'})
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                replay_study(report)

    def test_invalid_inputs_and_unknown_control_do_not_execute(self):
        from cx_eval_lab.knowledge_action import execute_trial, example_cases, example_documents
        case, docs = example_cases()[0], example_documents()
        for changes in ({'amount_cents': True}, {'age_days': -1}, {'currency': 'unknown'}, {'case_id': '../label'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                execute_trial(replace(case, **changes), docs, 'oracle', 'policy-control')
        for arm, agent in (('unknown', 'policy-control'), ('oracle', 'unregistered-code')):
            with self.assertRaises(ValueError):
                execute_trial(case, docs, arm, agent)
        with self.assertRaises(ValueError):
            execute_trial(case, (*docs, docs[0]), 'oracle', 'policy-control')

    def test_cli_retains_without_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'knowledge.json'
            command = [sys.executable, '-m', 'cx_eval_lab.knowledge_action', '--output', str(target)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            saved = target.read_bytes()
            self.assertTrue(json.loads(saved)['conformance_passed'])
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(saved, target.read_bytes())


if __name__ == '__main__':
    unittest.main()
