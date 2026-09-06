"""Actual local OTel/OTLP transport with independent request accounting; no remote telemetry."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import sqlite3
from pathlib import Path

import requests
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import NoOpMeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace import Status, StatusCode, set_span_in_context

from cx_eval_lab.agents import MutantSupportAgent, ReferenceSupportAgent
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import RefundCase
from cx_eval_lab.runner import evaluate_agent
from cx_eval_lab.telemetry_collector import (
    MODES,
    REQUESTS,
    RESOURCE,
    VERSION,
    LocalCollector,
    exact_fields,
    finite_copy,
    replay_delivery,
    require,
)

PRIVATE_CANARY = 'PRIVATE-TELEMETRY-CANARY-DO-NOT-EXPORT'
SCHEMA = 'local-otlp-study-v1'
SCOPE = 'Authored CX controls; in-memory collector and request ledger; no durable production acceptance.'
VERIFY_LIMIT = 'Retained HTTP consistency plus business-control reexecution, not independent proof of transport provenance.'
PACKAGES = ('opentelemetry-sdk', 'opentelemetry-api', 'opentelemetry-proto',
            'opentelemetry-exporter-otlp-proto-http', 'requests')
SOURCES = ('telemetry_collector.py', 'telemetry_study.py')


def _evaluate(index, canary):
    case = RefundCase(case_id=f'case-private-{index}', customer_id=f'customer-private-{index}',
        order_id=f'order-private-{index}', utterance=f'Refund please. {canary}', amount_cents=500,
        eligible=index not in {1, 2}, approval_threshold_cents=1000,
        expected_outcome='not_refunded' if index in {1, 2} else 'refunded', slices=('teaching',),
        simulate_timeout_after_commit=index == 3)
    agent = ReferenceSupportAgent() if index < 2 else MutantSupportAgent(
        'policy-bypass' if index == 2 else 'blind-retry')
    result = evaluate_agent(agent, (case,)).case_results[0]
    return {'request_id': REQUESTS[index], 'passed': result.passed,
            'tool_event_count': len(result.events),
            'failed_checks': [check.name for check in result.checks if not check.passed],
            'duplicate_refund_count': result.duplicate_refund_count,
            'unauthorized_action_count': result.unauthorized_action_count}


class _LoopbackSession(requests.Session):
    def __init__(self, endpoint):
        super().__init__()
        self.endpoint = endpoint
        self.trust_env = False
        self.headers.clear()
        self.auth = None
        self.cookies.clear()

    def send(self, request, **kwargs):
        require(request.method == 'POST' and request.url == self.endpoint, 'only fixed local collector permitted')
        require(not any(name in request.headers for name in ('Authorization', 'Proxy-Authorization', 'Cookie')),
                'ambient credentials prohibited')
        # Override inherited TLS credential settings too; no redirect or environment proxy escape.
        return super().send(request, **{**kwargs, 'cert': None, 'verify': True,
            'allow_redirects': False, 'proxies': {}})


class _RecordedExporter(OTLPSpanExporter):
    def __init__(self, endpoint):
        self.results = []
        super().__init__(endpoint=endpoint, headers={'x-evals-workshop': 'local'}, timeout=5,
            compression=Compression.NoCompression, session=_LoopbackSession(endpoint),
            meter_provider=NoOpMeterProvider())

    def export(self, spans):
        result = super().export(spans)
        ids = []
        for span in spans:
            if span.context is None:
                raise ValueError('exported span missing identity')
            ids = [*ids, f'{span.context.span_id:016x}']
        self.results = [*self.results, {'span_ids': ids, 'result': result.name}]
        return result


def _feedback(ledger):
    rows = [{'feedback_id': f'F{i + 1:02}', 'request_id': row['request_id'],
        'trace_id': row['trace_id'], 'evaluation_version': VERSION,
        'rating': 'positive' if i == 0 else 'negative'}
        for i, row in enumerate((ledger[0], ledger[2]))]
    return [*rows, dict(rows[0])]


def _ledger_lookup(ledger):
    require(isinstance(ledger, list) and len(ledger) == 4, 'complete request ledger required')
    for row in ledger:
        exact_fields(row, ('request_id', 'evaluation_version', 'trace_id', 'root_span_id', 'evaluation_span_id'))
        require(row['request_id'] in REQUESTS and row['evaluation_version'] == VERSION, 'unregistered request')
        for key, size in (('trace_id', 32), ('root_span_id', 16), ('evaluation_span_id', 16)):
            require(isinstance(row[key], str) and re.fullmatch(f'[0-9a-f]{{{size}}}', row[key])
                    and int(row[key], 16) > 0, 'invalid ledger identity')
    lookup = {row['request_id']: row for row in ledger}
    require(len(lookup) == len(ledger) and set(lookup) == set(REQUESTS), 'complete request ledger required')
    require(len({r['trace_id'] for r in ledger}) == 4 and
            len({r[k] for r in ledger for k in ('root_span_id', 'evaluation_span_id')}) == 8,
            'reused request/span identity')
    return lookup


def join_feedback(ledger, spans, feedback):
    """Authored structured feedback; unknown telemetry is pending, not a missing business request."""
    lookup = _ledger_lookup(ledger)
    roots = set()
    identities = set()
    for span in spans:
        exact_fields(span, ('trace_id', 'span_id', 'parent_span_id', 'name', 'start_ns', 'end_ns',
                            'attributes', 'resource'))
        attrs = span['attributes']
        exact_fields(attrs, ('request_id', 'evaluation_version', 'role', 'passed', 'tool_event_count'))
        require(attrs['request_id'] in lookup and attrs['role'] in {'request', 'evaluation'}, 'unknown span/request')
        row = lookup[attrs['request_id']]
        root = attrs['role'] == 'request'
        require((span['trace_id'], span['span_id'], span['parent_span_id'], attrs['evaluation_version']) ==
                (row['trace_id'], row['root_span_id'] if root else row['evaluation_span_id'],
                 '' if root else row['root_span_id'], row['evaluation_version']), 'feedback telemetry join mismatch')
        key = (span['trace_id'], span['span_id'])
        require(key not in identities, 'duplicate joined span')
        identities = identities | {key}
        if root:
            roots = roots | {attrs['request_id']}
    seen = {}
    joined = []
    duplicates = 0
    require(isinstance(feedback, list) and len(feedback) <= 20, 'bounded feedback required')
    for row in feedback:
        exact_fields(row, ('feedback_id', 'request_id', 'trace_id', 'evaluation_version', 'rating'))
        require(isinstance(row['feedback_id'], str) and row['feedback_id'].startswith('F')
                and len(row['feedback_id']) <= 40, 'feedback identity required')
        require(row['request_id'] in lookup and row['rating'] in {'positive', 'negative'}, 'invalid feedback')
        request = lookup[row['request_id']]
        require((row['trace_id'], row['evaluation_version']) ==
                (request['trace_id'], request['evaluation_version']), 'feedback cross-request/version mismatch')
        if row['feedback_id'] in seen:
            require(seen[row['feedback_id']] == row, 'conflicting feedback identity')
            duplicates += 1
            continue
        seen[row['feedback_id']] = dict(row)
        joined.append({**row, 'telemetry_state': 'joined' if row['request_id'] in roots else 'pending'})
    return {'rows': joined, 'duplicate_feedback': duplicates, 'unique_feedback': len(joined),
            'requests_with_feedback': len({row['request_id'] for row in joined}),
            'pending_feedback': sum(row['telemetry_state'] == 'pending' for row in joined)}


def _run_arm(mode, canary):
    with sqlite3.connect(':memory:') as db, LocalCollector(mode) as collector:
        db.execute('CREATE TABLE requests (request_id TEXT PRIMARY KEY, evaluation_version TEXT, '
                   'trace_id TEXT, root_span_id TEXT, evaluation_span_id TEXT)')
        db.executemany('INSERT INTO requests VALUES (?, ?, NULL, NULL, NULL)', [(r, VERSION) for r in REQUESTS])
        exporter = _RecordedExporter(collector.endpoint)
        provider = TracerProvider(resource=Resource(RESOURCE), sampler=ALWAYS_ON, shutdown_on_exit=False)
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = provider.get_tracer('cx.telemetry.study', '1')
        outcomes = []
        try:
            for index, request_id in enumerate(REQUESTS):
                root = tracer.start_span('cx.request', context=Context())
                child = tracer.start_span('cx.evaluate', context=set_span_in_context(root, Context()))
                db.execute('UPDATE requests SET trace_id=?, root_span_id=?, evaluation_span_id=? WHERE request_id=?',
                    (f'{root.get_span_context().trace_id:032x}', f'{root.get_span_context().span_id:016x}',
                     f'{child.get_span_context().span_id:016x}', request_id))
                result = _evaluate(index, canary)
                outcomes.append(result)
                for span, role in ((child, 'evaluation'), (root, 'request')):
                    span.set_attributes({'request_id': request_id, 'evaluation_version': VERSION,
                        'role': role, 'passed': result['passed'], 'tool_event_count': result['tool_event_count']})
                    span.set_status(Status(StatusCode.OK if result['passed'] else StatusCode.ERROR))
                    span.end()
            flushed = provider.force_flush(timeout_millis=5000)
        finally:
            provider.shutdown()
        cursor = db.execute('SELECT * FROM requests ORDER BY request_id')
        names = [field[0] for field in cursor.description]
        ledger = [dict(zip(names, values, strict=True)) for values in cursor.fetchall()]
        arm = {'mode': mode, 'ledger': ledger, 'business_results': outcomes,
            'attempts': finite_copy(collector.attempts), 'spans': finite_copy(collector.spans),
            'export_results': exporter.results, 'force_flush_returned': flushed,
            'feedback_input': _feedback(ledger)}
    return {**arm, 'summary': _summarize(arm),
            'feedback': join_feedback(ledger, arm['spans'], arm['feedback_input'])}


def _summarize(arm):
    roots = [span for span in arm['spans'] if span['attributes']['role'] == 'request']
    passes = sum(span['attributes']['passed'] for span in roots)
    return {'registered_requests': len(arm['ledger']), 'business_invocations': len(arm['business_results']),
        'ledger_passes': sum(row['passed'] for row in arm['business_results']),
        'ledger_failures': sum(not row['passed'] for row in arm['business_results']),
        'observed_roots': len(roots), 'known_passes': passes,
        'known_failures': len(roots) - passes, 'unknown_requests': len(arm['ledger']) - len(roots),
        'observed_pass_rate': passes / len(roots) if roots else None,
        'known_pass_fraction_all_requests': passes / len(arm['ledger']),
        'stored_spans': len(arm['spans']), 'http_attempts': len(arm['attempts']),
        'duplicate_deliveries': sum(row['duplicate'] for row in arm['attempts']),
        'export_failures': sum(row['result'] == 'FAILURE' for row in arm['export_results']),
        'status': 'hold' if len(roots) < len(arm['ledger']) else 'diagnostic_complete'}


def _validate_arm(arm):
    exact_fields(arm, ('mode', 'ledger', 'business_results', 'attempts', 'spans', 'export_results',
                      'force_flush_returned', 'feedback_input', 'summary', 'feedback'))
    require(arm['mode'] in MODES and type(arm['force_flush_returned']) is bool, 'invalid control')
    require(isinstance(arm['ledger'], list) and len(arm['ledger']) == 4, 'complete independent ledger required')
    require([r['request_id'] for r in arm['ledger']] == list(REQUESTS), 'request inventory mismatch')
    ledger = _ledger_lookup(arm['ledger'])
    stored, attempts = replay_delivery(arm['mode'], arm['attempts'])
    require(canonical_hash(stored) == canonical_hash(arm['spans']), 'stored spans mismatch')
    business = [_evaluate(i, PRIVATE_CANARY) for i in range(4)]
    require(canonical_hash(business) == canonical_hash(arm['business_results']), 'business reexecution mismatch')
    seen = {}
    for span in attempts:
        attrs = span['attributes']
        row = ledger[attrs['request_id']]
        evaluation = attrs['role'] == 'evaluation'
        expected_id = row['evaluation_span_id'] if evaluation else row['root_span_id']
        require(span['trace_id'] == row['trace_id'] and span['span_id'] == expected_id and
                span['parent_span_id'] == (row['root_span_id'] if evaluation else ''), 'parent/request join mismatch')
        expected = business[REQUESTS.index(attrs['request_id'])]
        require((attrs['passed'], attrs['tool_event_count']) ==
                (expected['passed'], expected['tool_event_count']), 'exported grade mismatch')
        key = (attrs['request_id'], attrs['role'])
        if key in seen:
            require(seen[key] == span and arm['mode'] == 'retry-dedup', 'unexpected duplicate span')
        seen[key] = span
    require(len(seen) == 8 and len({r['trace_id'] for r in ledger.values()}) == 4,
            'all request/evaluation attempts must remain visible')
    export_expected = []
    for request_id in REQUESTS:
        for role in ('evaluation', 'request'):
            span = seen[(request_id, role)]
            accepted = span in stored
            export_expected.append({'span_ids': [span['span_id']], 'result': 'SUCCESS' if accepted else 'FAILURE'})
    require(export_expected == arm['export_results'], 'export result mismatch')
    require(canonical_hash(_summarize(arm)) == canonical_hash(arm['summary']), 'summary mismatch')
    require(canonical_hash(_feedback(arm['ledger'])) == canonical_hash(arm['feedback_input']), 'feedback fixture mismatch')
    require(canonical_hash(join_feedback(arm['ledger'], stored, arm['feedback_input'])) ==
            canonical_hash(arm['feedback']), 'feedback join mismatch')


def stable_projection(report):
    """Compare fresh real executions without claiming wall-clock or random-ID byte reproducibility."""
    return [{'mode': arm['mode'], 'business_results': arm['business_results'], 'summary': arm['summary'],
             'feedback': {key: value for key, value in arm['feedback'].items() if key != 'rows'}}
            for arm in report['arms']]


def run_study():
    report = {'schema': SCHEMA, 'evidence_kind': 'local_sdk_otlp_http_control',
        'manifest': {'python': platform.python_version(),
            'packages': {name: importlib.metadata.version(name) for name in PACKAGES},
            'source_hashes': {f'cx_eval_lab/{name}': hashlib.sha256(
                Path(__file__).with_name(name).read_bytes()).hexdigest() for name in SOURCES}},
        'scope': SCOPE, 'verification_limit': VERIFY_LIMIT,
        'verification_business_invocations_per_call': 16,
        'deployment_authorized': False, 'evaluation_version': VERSION,
        'arms': [_run_arm(mode, PRIVATE_CANARY) for mode in MODES]}
    return {**report, 'content_hash': canonical_hash(report)}


def verify_study(report):
    report = finite_copy(report)
    exact_fields(report, ('schema', 'evidence_kind', 'scope', 'verification_limit', 'deployment_authorized',
                          'evaluation_version', 'arms', 'content_hash', 'verification_business_invocations_per_call',
                          'manifest'))
    require(report['schema'] == SCHEMA and report['evidence_kind'] == 'local_sdk_otlp_http_control'
            and report['deployment_authorized'] is False and report['evaluation_version'] == VERSION,
            'study contract mismatch')
    manifest = report['manifest']
    exact_fields(manifest, ('python', 'packages', 'source_hashes'))
    exact_fields(manifest['packages'], PACKAGES)
    exact_fields(manifest['source_hashes'], (f'cx_eval_lab/{name}' for name in SOURCES))
    require(isinstance(manifest['python'], str) and re.fullmatch(r'3\.\d+\.\d+', manifest['python']),
            'Python execution version required')
    for name, version in manifest['packages'].items():
        require(isinstance(version, str) and (re.fullmatch(r'\d+\.\d+\.\d+', version)
                if name == 'requests' else version == '1.44.0'), 'unsupported recorded package version')
    for digest in manifest['source_hashes'].values():
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'source digest required')
    require(report['scope'] == SCOPE and report['verification_limit'] == VERIFY_LIMIT and
            type(report['verification_business_invocations_per_call']) is int and
            report['verification_business_invocations_per_call'] == 16, 'verification scope mismatch')
    require(canonical_hash({k: v for k, v in report.items() if k != 'content_hash'}) == report['content_hash'],
            'study hash mismatch')
    require([arm['mode'] for arm in report['arms']] == list(MODES), 'complete control inventory required')
    for arm in report['arms']:
        _validate_arm(arm)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'output already exists')
    report = verify_study(run_study())
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
