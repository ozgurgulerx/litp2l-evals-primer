"""Native multi-order executions must survive paired projection and re-grading."""

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

    def test_rehashed_measurements_must_match_their_retained_source(self):
        packet = packet_for()
        artifact = packet['trial_artifacts'][0]
        payload = artifact['payload']
        for key, value in (('latency_ms', 999999), ('cost_usd', 123.0)):
            payload[key] = payload['evaluation'][key] = value
            next(r for r in packet['baseline_trials'] if r['artifact_hash'] == artifact['artifact_hash'])[key] = value
        rehash(packet)
        with self.assertRaisesRegex(ValueError, 'measurement'):
            replay_packet(packet)

    def test_declared_arm_execution_order_matches_retained_artifact_sequence(self):
        packet = packet_for()
        packet['trial_artifacts'][0:2] = reversed(packet['trial_artifacts'][0:2])
        with self.assertRaisesRegex(ValueError, 'execution order'):
            replay_packet(packet)

    def test_malformed_output_and_execution_error_fail_with_validation_error(self):
        for field, value in (('output', []), ('execution_error', []), ('elapsed_ms', float('nan'))):
            packet = packet_for()
            packet['trial_artifacts'][0]['payload'][field] = value
            rehash(packet)
            with self.subTest(field=field), self.assertRaises(ValueError):
                replay_packet(packet)

    def test_boolean_row_index_is_not_an_integer_trial_identity(self):
        packet = packet_for()
        packet['baseline_trials'][0]['trial_index'] = False
        with self.assertRaises(ValueError):
            replay_packet(packet)

    def test_measured_mock_execution_binds_elapsed_time_and_unknown_runtime_cost(self):
        from dataclasses import replace
        from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
        cases, agent = example_cases(), DescriptiveResolver()
        manifest = replace(make_manifest(cases, agent.name, agent.name),
                           measurement_kind='measured', code_revision='local-test-fixture')
        packet = run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                      manifest=manifest, measurement_profile=None).to_dict()
        results = replay_packet(packet)
        self.assertTrue(all(r.cost_usd is None for r in results))
        payload = packet['trial_artifacts'][0]['payload']
        payload['elapsed_ms'] += 100
        rehash(packet)
        with self.assertRaisesRegex(ValueError, 'measurement'):
            replay_packet(packet)

    def test_native_prose_cannot_self_qualify_and_current_assessment_reports_gap(self):
        from datetime import datetime, timezone
        from cx_eval_lab.replay_authority import assess_replay
        from cx_eval_lab.semantic import CalibrationRegistry
        packet = packet_for()
        assessment = assess_replay(packet, trusted_packet_hash=canonical_hash(packet),
            historical_calibration_hashes=frozenset(), registry=CalibrationRegistry(()),
            now=datetime(2026, 9, 6, tzinfo=timezone.utc))
        self.assertEqual(16, assessment.unqualified_message_trials)
        self.assertEqual('not_applicable', assessment.calibration_status)
        packet['trial_artifacts'][0]['payload']['semantic_message_qualified'] = True
        rehash(packet)
        with self.assertRaisesRegex(ValueError, 'semantic qualification unsupported'):
            replay_packet(packet)

    def test_denial_survives_replay_after_a_correct_action(self):
        class DeniedThenCorrect(DescriptiveResolver):
            name = 'denied-then-correct'
            def run(self, request, tools):
                try:
                    tools.get_order('order-c')
                except PermissionError:
                    pass
                return super().run(request, tools)
        packet = packet_for(DeniedThenCorrect())
        results = replay_packet(packet)[8:]
        self.assertTrue(all(not r.passed for r in results))
        self.assertTrue(all(not next(c for c in r.checks if c.name == 'denied_attempts').passed
                            for r in results))

    def test_ineligible_expected_refund_does_not_disappear_from_paired_evidence(self):
        from dataclasses import replace
        from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
        case = example_cases()[0]
        case = replace(case, orders=tuple(replace(r, eligible=False) for r in case.orders))
        agent = DescriptiveResolver()
        manifest = make_manifest((case,), agent.name, agent.name)
        packet = run_paired_resolution(cases=(case,), baseline_agent=agent, candidate_agent=agent,
                                      manifest=manifest).to_dict()
        self.assertTrue(all(not r.passed for r in replay_packet(packet)))


if __name__ == '__main__':
    unittest.main()
