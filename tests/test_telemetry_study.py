"""Local SDK/OTLP delivery evidence, independent coverage and feedback joins."""

import base64
import copy
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


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

    def test_all_actual_wire_bytes_exclude_private_canary_and_environment_credentials(self):
        from opentelemetry.trace import get_tracer_provider

        from cx_eval_lab.telemetry_study import PRIVATE_CANARY, _run_arm
        provider = get_tracer_provider()
        ambient = {'OTEL_EXPORTER_OTLP_HEADERS': f'Authorization={PRIVATE_CANARY}',
            'OTEL_EXPORTER_OTLP_TRACES_HEADERS': f'Cookie={PRIVATE_CANARY}',
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://192.0.2.1:4318/',
            'OTEL_RESOURCE_ATTRIBUTES': f'host.name={PRIVATE_CANARY}',
            'OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE': '/nonexistent/private.pem',
            'HTTP_PROXY': 'http://192.0.2.1:9999', 'NO_PROXY': ''}
        with patch.dict(os.environ, ambient):
            arm = _run_arm('normal', PRIVATE_CANARY)
        self.assertIs(provider, get_tracer_provider())
        self.assertEqual(8, len(arm['spans']))
        for attempt in arm['attempts']:
            self.assertNotIn(PRIVATE_CANARY.encode(), base64.b64decode(attempt['payload_b64']))

    def test_exception_text_is_not_added_to_sdk_events_or_status(self):
        from cx_eval_lab.telemetry_study import PRIVATE_CANARY, _run_arm
        with patch('cx_eval_lab.agents.ReferenceSupportAgent.run', side_effect=RuntimeError(PRIVATE_CANARY)):
            arm = _run_arm('normal', PRIVATE_CANARY)
        self.assertEqual(0, arm['summary']['ledger_passes'])
        self.assertNotIn(PRIVATE_CANARY, json.dumps(arm))
        for attempt in arm['attempts']:
            self.assertNotIn(PRIVATE_CANARY.encode(), base64.b64decode(attempt['payload_b64']))

    def test_protobuf_allowlist_rejects_unfiltered_private_fields_and_invalid_types(self):
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )

        from cx_eval_lab.telemetry_collector import decode_payload
        original = base64.b64decode(self.report['arms'][0]['attempts'][0]['payload_b64'])
        for mode in ('resource', 'scope', 'event', 'status', 'state', 'bool', 'negative-count',
                     'trace', 'parent', 'time', 'scope-name', 'multiple', 'dropped', 'unknown-wire'):
            message = ExportTraceServiceRequest.FromString(original)
            resource = message.resource_spans[0]
            scope = resource.scope_spans[0]
            span = scope.spans[0]
            if mode == 'resource':
                resource.resource.attributes.add(key='host.name').value.string_value = 'private'
            elif mode == 'scope':
                scope.scope.attributes.add(key='private').value.string_value = 'secret'
            elif mode == 'event':
                span.events.add(name='private')
            elif mode == 'status':
                span.status.message = 'private'
            elif mode == 'state':
                span.trace_state = 'private'
            elif mode == 'bool':
                next(a for a in span.attributes if a.key == 'passed').value.string_value = 'true'
            elif mode == 'negative-count':
                next(a for a in span.attributes if a.key == 'tool_event_count').value.int_value = -1
            elif mode == 'trace':
                span.trace_id = bytes(16)
            elif mode == 'parent':
                span.parent_span_id = b''
            elif mode == 'time':
                span.end_time_unix_nano = 0
            elif mode == 'scope-name':
                scope.scope.name = 'unknown'
            elif mode == 'multiple':
                scope.spans.add().CopyFrom(span)
            elif mode == 'dropped':
                span.dropped_attributes_count = 1
            wire = message.SerializeToString() + (b'\xf8\x07\x01' if mode == 'unknown-wire' else b'')
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                decode_payload(wire)
        for body in (b'', b'not protobuf', b'x' * 65537):
            with self.assertRaises(ValueError):
                decode_payload(body)

    def test_collector_rejects_oversized_malformed_and_unexpected_http_requests(self):
        from cx_eval_lab.telemetry_collector import LocalCollector
        with LocalCollector('normal') as collector:
            for path, body, length, content in (('/v1/traces', b'', '65537', 'application/x-protobuf'),
                ('/wrong', b'x', '1', 'application/x-protobuf'),
                ('/v1/traces', b'bad', '3', 'application/x-protobuf'),
                ('/v1/traces', b'x', '1', 'application/json')):
                connection = http.client.HTTPConnection(*collector.server.server_address, timeout=3)
                connection.request('POST', path, body, headers={'Content-Length': length, 'Content-Type': content})
                self.assertEqual(400, connection.getresponse().status)
                connection.close()
            self.assertEqual([], collector.spans)

    def test_coherent_payload_parent_tamper_rejected_at_ledger_join(self):
        import hashlib

        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )

        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.telemetry_collector import decode_payload
        from cx_eval_lab.telemetry_study import verify_study
        bad = copy.deepcopy(self.report)
        attempt = bad['arms'][0]['attempts'][0]
        message = ExportTraceServiceRequest.FromString(base64.b64decode(attempt['payload_b64']))
        message.resource_spans[0].scope_spans[0].spans[0].parent_span_id = bytes.fromhex('a' * 16)
        body = message.SerializeToString()
        attempt.update(payload_b64=base64.b64encode(body).decode(), payload_sha256=hashlib.sha256(body).hexdigest(),
                       body_bytes=len(body))
        bad['arms'][0]['spans'][0] = decode_payload(body)
        bad['content_hash'] = canonical_hash({k: v for k, v in bad.items() if k != 'content_hash'})
        with self.assertRaises(ValueError):
            verify_study(bad)

    def test_retained_artifact_verifies_and_matches_fresh_stable_projection(self):
        from cx_eval_lab.telemetry_study import stable_projection, verify_study
        path = Path(__file__).resolve().parents[1] / 'docs/assets/telemetry-study-v1.json'
        retained = json.loads(path.read_text())
        self.assertEqual(retained, verify_study(retained))
        self.assertEqual(stable_projection(self.report), stable_projection(retained))

    def test_cli_exclusive_output_and_reexecution_verifier(self):
        from cx_eval_lab.telemetry_study import verify_study
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'study.json'
            command = [sys.executable, '-m', 'cx_eval_lab.telemetry_study', '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(report, verify_study(report))
            original = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(0, second.returncode)
            self.assertEqual(original, output.read_bytes())


if __name__ == '__main__':
    unittest.main()
