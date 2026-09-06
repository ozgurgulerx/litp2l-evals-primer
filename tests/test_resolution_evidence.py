"""Native multi-order executions must survive paired projection and re-grading."""

import copy
import unittest
from unittest.mock import patch

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.order_resolution import DescriptiveResolver, FirstRecordResolver, example_cases


def packet_for(candidate=None):
    from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
    baseline, candidate = DescriptiveResolver(), candidate or FirstRecordResolver()
    cases = example_cases()
    manifest = make_manifest(cases, baseline.name, candidate.name)
    return run_paired_resolution(cases=cases, baseline_agent=baseline,
                                 candidate_agent=candidate, manifest=manifest).to_dict()


def rehash(packet):
    for artifact in packet['trial_artifacts']:
        old = artifact['artifact_hash']
        artifact['artifact_hash'] = canonical_hash(artifact['payload'])
        for row in (*packet['baseline_trials'], *packet['candidate_trials']):
            if row['artifact_hash'] == old:
                row['artifact_hash'] = artifact['artifact_hash']


class ResolutionEvidenceTests(unittest.TestCase):
    def test_native_pairs_replay_without_agents_and_keep_customer_clustering(self):
        packet = packet_for()
        with patch.object(DescriptiveResolver, 'run', side_effect=AssertionError('agent invoked')):
            results = replay_packet(packet)
        self.assertEqual(16, len(results))
        self.assertEqual(8, sum(row['passed'] for row in packet['baseline_trials']))
        self.assertEqual(2, sum(row['passed'] for row in packet['candidate_trials']))
        self.assertEqual({'customer-1'}, {r['cluster_id'] for r in packet['baseline_trials']})
        for artifact in packet['trial_artifacts']:
            payload = artifact['payload']
            self.assertEqual('resolution-trial-v1', payload['schema'])
            self.assertEqual({'customer_id', 'utterance'}, set(payload['agent_input']))
            self.assertEqual(3, len(payload['orders']))
            self.assertFalse(payload['semantic_message_qualified'])
        unresolved = [r for r in results if r.case_id == 'unresolved-description']
        self.assertTrue(any(r.passed and not r.task_completed for r in unresolved))

    def test_registered_cases_request_schedule_and_arm_cannot_be_rewritten(self):
        for field, value in (('agent_input', {'customer_id':'customer-1', 'utterance':'changed'}),
                             ('reverse', True), ('agent', 'different-agent')):
            packet = packet_for()
            packet['trial_artifacts'][0]['payload'][field] = value
            rehash(packet)
            with self.subTest(field=field), self.assertRaises(ValueError):
                replay_packet(packet)
        packet = packet_for()
        packet['trial_artifacts'][0]['payload']['case']['expected_order_id'] = 'order-a'
        rehash(packet)
        with self.assertRaises(ValueError):
            replay_packet(packet)

    def test_changed_results_missing_events_and_foreign_state_are_detected_after_rehash(self):
        for mutation in ('result', 'event', 'foreign-state', 'unsupported-tool'):
            packet = packet_for()
            payload = packet['trial_artifacts'][0]['payload']
            if mutation == 'result':
                payload['tool_events'][0]['result'].clear()
            elif mutation == 'event':
                payload['tool_events'].pop()
            elif mutation == 'foreign-state':
                next(r for r in payload['orders'] if r['order']['order_id'] == 'order-c')[
                    'state']['refund_transaction_count'] = 1
            else:
                payload['tool_events'][0]['tool'] = '__getattribute__'
            rehash(packet)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                replay_packet(packet)

    def test_case_membership_is_registered_beyond_remaining_pair_completeness(self):
        packet = packet_for()
        removed = {a['artifact_hash'] for a in packet['trial_artifacts']
                   if a['payload']['case']['case_id'] == 'customer-correction'}
        packet['trial_artifacts'] = [a for a in packet['trial_artifacts'] if a['artifact_hash'] not in removed]
        for arm in ('baseline', 'candidate'):
            packet[f'{arm}_trials'] = [r for r in packet[f'{arm}_trials'] if r['artifact_hash'] not in removed]
        with self.assertRaises(ValueError):
            replay_packet(packet)

    def test_execution_error_is_retained_without_raw_exception_message(self):
        class Broken(DescriptiveResolver):
            name = 'broken'
            def run(self, request, tools):
                raise RuntimeError('private error details')
        packet = packet_for(Broken())
        results = replay_packet(packet)
        self.assertEqual(8, sum(r.passed for r in results))
        self.assertNotIn('private error details', str(packet))

    def test_manifest_mismatch_fails_before_any_agent_call(self):
        from dataclasses import replace
        from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
        cases, agent = example_cases(), DescriptiveResolver()
        manifest = make_manifest(cases, agent.name, agent.name)
        for changes in ({'dataset_version':'wrong'}, {'estimand':'overall_agent_quality'},
                        {'input_hashes': (('resolution-cases', canonical_hash('wrong')),)}):
            with patch.object(agent, 'run', side_effect=AssertionError('agent invoked')) as execute:
                with self.assertRaises(ValueError):
                    run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                          manifest=replace(manifest, **changes))
                execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
