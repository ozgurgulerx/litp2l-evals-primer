"""Bounded loopback OTLP test collector; acknowledgements mean in-memory acceptance."""

import base64
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)

MAX_BODY = 65536
MODES = ('normal', 'capacity', 'reject', 'retry-dedup')
ATTRIBUTES = {'request_id', 'evaluation_version', 'role', 'passed', 'tool_event_count'}
RESOURCE = {'service.name': 'cx-telemetry-teaching'}
VERSION = 'telemetry-eval-v1'
REQUESTS = ('R01', 'R02', 'R03', 'R04')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_fields(value, names):
    require(isinstance(value, dict) and set(value) == set(names), 'unexpected fields')


def _attributes(values):
    result = {}
    for attr in values:
        require(attr.key not in result, 'duplicate attribute')
        kind = attr.value.WhichOneof('value')
        require(kind in {'string_value', 'bool_value', 'int_value'}, 'unsupported attribute type')
        result[attr.key] = getattr(attr.value, kind)
    return result


def decode_payload(body):
    """Validate the actual protobuf bytes, not an asserted exported-field projection."""
    require(isinstance(body, bytes) and 0 < len(body) <= MAX_BODY, 'bounded OTLP body required')
    message = ExportTraceServiceRequest()
    try:
        message.ParseFromString(body)
    except Exception as exc:
        raise ValueError('invalid OTLP protobuf') from exc
    before = message.SerializeToString()
    message.DiscardUnknownFields()
    require(before == message.SerializeToString(), 'unknown protobuf fields')
    require(len(message.resource_spans) == 1, 'one registered resource required')
    resource = message.resource_spans[0]
    require(_attributes(resource.resource.attributes) == RESOURCE, 'resource allowlist mismatch')
    require(not resource.schema_url and not resource.resource.dropped_attributes_count,
            'unexpected resource metadata')
    require(len(resource.scope_spans) == 1, 'one instrumentation scope required')
    scope = resource.scope_spans[0]
    require(scope.scope.name == 'cx.telemetry.study' and scope.scope.version == '1', 'unknown scope')
    require(not scope.scope.attributes and not scope.schema_url and not scope.scope.dropped_attributes_count,
            'unexpected scope metadata')
    require(len(scope.spans) == 1, 'SimpleSpanProcessor emits one span per request here')
    span = scope.spans[0]
    attrs = _attributes(span.attributes)
    exact_fields(attrs, ATTRIBUTES)
    require(attrs['request_id'] in REQUESTS and attrs['evaluation_version'] == VERSION,
            'unregistered request or evaluation')
    require(attrs['role'] in {'request', 'evaluation'}, 'unknown span role')
    require(type(attrs['passed']) is bool, 'exact boolean grade required')
    require(type(attrs['tool_event_count']) is int and 0 <= attrs['tool_event_count'] <= 100,
            'bounded event count required')
    require(span.name == ('cx.request' if attrs['role'] == 'request' else 'cx.evaluate'), 'span name mismatch')
    require(len(span.trace_id) == 16 and any(span.trace_id) and len(span.span_id) == 8 and any(span.span_id),
            'nonzero trace/span identity required')
    require((not span.parent_span_id if attrs['role'] == 'request' else
             len(span.parent_span_id) == 8 and any(span.parent_span_id)), 'invalid span parent')
    require(span.start_time_unix_nano > 0 and span.end_time_unix_nano >= span.start_time_unix_nano,
            'invalid span timing')
    require(not span.events and not span.links and not span.status.message and not span.trace_state,
            'raw events, links, status text and trace state prohibited')
    require(not span.dropped_attributes_count and not span.dropped_events_count and not span.dropped_links_count,
            'SDK truncation must not be hidden')
    require(span.status.code == (1 if attrs['passed'] else 2) and span.kind == 1, 'span status mismatch')
    return {'trace_id': span.trace_id.hex(), 'span_id': span.span_id.hex(),
            'parent_span_id': span.parent_span_id.hex(), 'name': span.name,
            'start_ns': span.start_time_unix_nano, 'end_ns': span.end_time_unix_nano,
            'attributes': attrs, 'resource': RESOURCE.copy()}


def delivery_step(mode, stored, span, attempt_index):
    """Collector decision; actual HTTP transport invokes this same bounded rule."""
    require(mode in MODES, 'unknown collector mode')
    key = (span['trace_id'], span['span_id'])
    prior = next((x for x in stored if (x['trace_id'], x['span_id']) == key), None)
    if prior is not None:
        require(prior == span, 'conflicting repeated span identity')
        return 200, list(stored), True
    if mode == 'reject' or (mode == 'capacity' and len(stored) >= 4):
        return 400, list(stored), False
    return (503 if mode == 'retry-dedup' and attempt_index == 0 else 200), [*stored, span], False


class LocalCollector:
    """Local test receiver. No disk persistence, authentication service or remote export."""

    def __init__(self, mode):
        require(mode in MODES, 'unknown collector mode')
        self.mode = mode
        self.spans = []
        self.attempts = []
        collector = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(0.5)  # Bound request-line and header parsing too.

            def log_message(self, format, *args):
                return  # Never log caller-supplied text or HTTP headers.

            def do_POST(self):
                self.connection.settimeout(2)
                status = 400
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    require(self.path == '/v1/traces' and self.headers.get('Transfer-Encoding') is None,
                            'unsupported path or transfer encoding')
                    require(0 < size <= MAX_BODY, 'request body limit')
                    require(self.headers.get('Content-Type') == 'application/x-protobuf', 'invalid content type')
                    body = self.rfile.read(size)
                    require(len(body) == size, 'incomplete body')
                    span = decode_payload(body)
                    status, stored, duplicate = delivery_step(collector.mode, collector.spans, span,
                                                               len(collector.attempts))
                    collector.spans = stored  # Store before the response, including injected lost acknowledgement.
                    collector.attempts = [*collector.attempts, {'status_code': status, 'payload_b64': base64.b64encode(body).decode(),
                        'payload_sha256': hashlib.sha256(body).hexdigest(), 'body_bytes': len(body),
                        'duplicate': duplicate}]
                except (ValueError, OSError):
                    status = 400  # No exception details or rejected raw bodies retained.
                self.send_response(status)
                self.send_header('Content-Type', 'application/x-protobuf')
                self.send_header('Content-Length', '0')
                self.end_headers()

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.endpoint = f'http://127.0.0.1:{self.server.server_port}/v1/traces'
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': 0.01}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def replay_delivery(mode, attempts):
    require(isinstance(attempts, list) and 8 <= len(attempts) <= 9, 'incomplete bounded delivery log')
    stored = []
    observed = []
    for index, attempt in enumerate(attempts):
        exact_fields(attempt, ('status_code', 'payload_b64', 'payload_sha256', 'body_bytes', 'duplicate'))
        try:
            body = base64.b64decode(attempt['payload_b64'], validate=True)
        except Exception as exc:
            raise ValueError('invalid retained payload') from exc
        require(hashlib.sha256(body).hexdigest() == attempt['payload_sha256'], 'payload hash mismatch')
        require(type(attempt['body_bytes']) is int and attempt['body_bytes'] == len(body), 'body length mismatch')
        require(type(attempt['status_code']) is int and type(attempt['duplicate']) is bool, 'exact transport types')
        span = decode_payload(body)
        status, stored, duplicate = delivery_step(mode, stored, span, index)
        require((status, duplicate) == (attempt['status_code'], attempt['duplicate']), 'delivery outcome mismatch')
        observed.append(span)
    require(len(attempts) == (9 if mode == 'retry-dedup' else 8), 'retry count mismatch')
    return stored, observed


def finite_copy(value):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (ValueError, TypeError) as exc:
        raise ValueError('finite JSON required') from exc
