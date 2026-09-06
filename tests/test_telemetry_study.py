"""Local SDK/OTLP delivery evidence, independent coverage and feedback joins."""

import copy
import json
import socket
import threading
import unittest


class TelemetryStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cx_eval_lab.telemetry_study import run_study
        cls.report = run_study()

    def test_actual_delivery_controls_keep_independent_denominator(self):
        rows = {arm['mode']: arm['summary'] for arm in self.report['arms']}
        for mode, roots, passes, unknown in (
            ('normal', 4, 2, 0), ('capacity', 2, 2, 2),
            ('reject', 0, 0, 4), ('retry-dedup', 4, 2, 0),
        ):
            self.assertEqual(4, rows[mode]['registered_requests'])
            self.assertEqual(roots, rows[mode]['observed_roots'])
            self.assertEqual(passes, rows[mode]['known_passes'])
            self.assertEqual(unknown, rows[mode]['unknown_requests'])
        self.assertEqual(1.0, rows['capacity']['observed_pass_rate'])
        self.assertEqual(0.5, rows['capacity']['known_pass_fraction_all_requests'])
        self.assertIsNone(rows['reject']['observed_pass_rate'])
        self.assertFalse(self.report['deployment_authorized'])

    def test_retry_is_real_http_repeated_payload_with_one_stored_span(self):
        retry = next(arm for arm in self.report['arms'] if arm['mode'] == 'retry-dedup')
        self.assertEqual([503, 200], [x['status_code'] for x in retry['attempts'][:2]])
        self.assertEqual(retry['attempts'][0]['payload_sha256'], retry['attempts'][1]['payload_sha256'])
        self.assertEqual(9, len(retry['attempts']))
        self.assertEqual(8, len(retry['spans']))
        self.assertEqual(1, retry['summary']['duplicate_deliveries'])

    def test_no_private_text_or_ambient_resource_metadata_in_report(self):
        from cx_eval_lab.telemetry_study import PRIVATE_CANARY
        text = json.dumps(self.report)
        self.assertNotIn(PRIVATE_CANARY, text)
        for forbidden in ('host.name', 'process.command', 'customer-private', 'order-private'):
            self.assertNotIn(forbidden, text)

    def test_verified_record_rejects_rehashed_omission_and_wrong_parent(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.telemetry_study import verify_study
        self.assertEqual(self.report, verify_study(self.report))
        for field in ('ledger', 'attempts', 'spans'):
            bad = copy.deepcopy(self.report)
            bad['arms'][0][field].pop()
            bad['content_hash'] = canonical_hash({k: v for k, v in bad.items() if k != 'content_hash'})
            with self.assertRaises(ValueError):
                verify_study(bad)

    def test_feedback_join_rejects_conflicting_duplicate_and_cross_request(self):
        from cx_eval_lab.telemetry_study import join_feedback
        arm = self.report['arms'][0]
        feedback = arm['feedback_input']
        self.assertEqual(1, join_feedback(arm['ledger'], arm['spans'], feedback)['duplicate_feedback'])
        conflict = copy.deepcopy(feedback[0])
        conflict['rating'] = 'negative'
        with self.assertRaises(ValueError):
            join_feedback(arm['ledger'], arm['spans'], feedback + [conflict])
        mismatch = copy.deepcopy(feedback[0])
        mismatch['request_id'] = 'R04'
        with self.assertRaises(ValueError):
            join_feedback(arm['ledger'], arm['spans'], [mismatch])

    def test_standalone_feedback_rejects_forged_trace_and_duplicate_roots(self):
        from cx_eval_lab.telemetry_study import join_feedback
        arm = self.report['arms'][0]
        for mode in ('trace', 'span', 'version', 'duplicate'):
            spans = copy.deepcopy(arm['spans'])
            root = next(s for s in spans if s['attributes']['role'] == 'request')
            if mode == 'trace':
                root['trace_id'] = 'a' * 32
            elif mode == 'span':
                root['span_id'] = 'a' * 16
            elif mode == 'version':
                root['attributes']['evaluation_version'] = 'unregistered'
            else:
                spans.append(copy.deepcopy(root))
            with self.assertRaises(ValueError):
                join_feedback(arm['ledger'], spans, arm['feedback_input'])

    def test_idle_socket_cannot_hang_collector_shutdown(self):
        from cx_eval_lab.telemetry_collector import LocalCollector
        collector = LocalCollector('normal').__enter__()
        connection = socket.create_connection(collector.server.server_address, timeout=2)
        connection.sendall(b'POST /v1/traces HTTP/1.1\r\n')
        shutdown = threading.Thread(target=collector.__exit__, daemon=True)
        shutdown.start()
        try:
            shutdown.join(timeout=3)
            self.assertFalse(shutdown.is_alive(), 'partial HTTP headers must have a bounded timeout')
        finally:
            connection.close()
            shutdown.join(timeout=3)

    def test_rehashed_unsupported_scope_claim_is_rejected(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.telemetry_study import verify_study
        bad = copy.deepcopy(self.report)
        bad['scope'] = 'Durable production proof'
        bad['content_hash'] = canonical_hash({k: v for k, v in bad.items() if k != 'content_hash'})
        with self.assertRaises(ValueError):
            verify_study(bad)


if __name__ == '__main__':
    unittest.main()
