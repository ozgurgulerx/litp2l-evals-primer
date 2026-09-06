"""Synthetic run-cache isolation with SQLite and explicitly ordered thread overlap."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import threading

from cx_eval_lab.evidence import canonical_hash

POLICY = {'policy': 'synthetic-shared-readonly-v1'}
QUERY = 'What is the status of my synthetic case?'
STRATEGIES = ('query-only', 'scoped')
CONTEXTS = ('fresh-workers', 'reused-worker', 'concurrent-threads')
WORKERS = {'fresh-workers': ('worker-1', 'worker-2', 'worker-3'),
           'reused-worker': ('worker-shared',) * 3, 'concurrent-threads': ('worker-A', 'worker-B', 'worker-A')}
TIMEOUT = 5


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('bounded opaque operator identity required')


def _key(strategy, run_id, operation, query):
    if operation.startswith('private_'):
        return ('private', run_id if strategy == 'scoped' else '*', canonical_hash(query))
    return ('shared-policy', '*', 'policy-v1')


@dataclass(frozen=True)
class RunContext:
    run_id: str
    token: object = field(repr=False)


class CacheStore:
    """Operator-owned facade. Python handles are not a hostile-code sandbox."""

    def __init__(self, path, strategy):
        if strategy not in STRATEGIES or Path(path).exists():
            raise ValueError('registered strategy and new isolated database required')
        self.path, self.strategy, self._contexts = Path(path), strategy, {}
        with closing(self._db()) as db, db:
            db.execute('CREATE TABLE entries(namespace TEXT,scope TEXT,key TEXT,value TEXT, '
                       'PRIMARY KEY(namespace,scope,key))')
            db.execute('CREATE TABLE calls(seq INTEGER PRIMARY KEY, payload TEXT)')
            db.execute('INSERT INTO entries VALUES (?,?,?,?)',
                       ('shared-policy', '*', 'policy-v1', json.dumps(POLICY)))

    def _db(self):
        return sqlite3.connect(self.path, timeout=TIMEOUT)

    def issue_context(self, run_id):
        _identifier(run_id)
        token = object()
        self._contexts = {**self._contexts, token: run_id}
        return RunContext(run_id, token)

    def call(self, context, worker_id, operation, query=None, value=None):
        if not isinstance(context, RunContext) or self._contexts.get(context.token) != context.run_id:
            raise PermissionError('operator-issued run context required')
        _identifier(worker_id)
        if operation not in ('private_read', 'private_write', 'policy_read', 'policy_write_denied', 'worker_ready'):
            raise ValueError('unknown cache operation')
        if operation.startswith('private_') and (not isinstance(query, str) or not 1 <= len(query) <= 1024):
            raise ValueError('bounded query text required')
        key = _key(self.strategy, context.run_id, operation, query)
        value = json.loads(json.dumps(value, allow_nan=False))
        with closing(self._db()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if operation in ('private_read', 'policy_read'):
                row = db.execute('SELECT value FROM entries WHERE namespace=? AND scope=? AND key=?', key).fetchone()
                value = None if row is None else json.loads(row[0])
            elif operation == 'private_write':
                if value != {'private_marker': context.run_id}:
                    raise ValueError('only own synthetic marker may be written')
                db.execute('INSERT INTO entries VALUES (?,?,?,?)', (*key, json.dumps(value)))
            payload = {'run_id': context.run_id, 'worker_id': worker_id,
                'thread_id': threading.get_ident(), 'operation': operation,
                'query': query, 'storage_key': list(key), 'value': value}
            sequence = db.execute('INSERT INTO calls(payload) VALUES (?)',
                                  (json.dumps(payload, allow_nan=False),)).lastrowid
        if operation == 'policy_write_denied':
            raise PermissionError('shared policy is immutable')
        return value, sequence

    def snapshot(self):
        with closing(self._db()) as db:
            return [{'storage_key': list(row[:3]), 'value': json.loads(row[3])}
                    for row in db.execute('SELECT * FROM entries ORDER BY namespace,scope,key')]

    def calls(self):
        with closing(self._db()) as db:
            return [{'sequence': sequence, **json.loads(payload)}
                    for sequence, payload in db.execute('SELECT * FROM calls ORDER BY seq')]


@dataclass(frozen=True)
class Worker:
    store: CacheStore = field(repr=False)
    worker_id: str

    def resolve(self, context, query):
        value, read = self.store.call(context, self.worker_id, 'private_read', query)
        write = None
        if value is None:
            value = {'private_marker': context.run_id}
            _, write = self.store.call(context, self.worker_id, 'private_write', query, value)
        return {'run_id': context.run_id, 'worker_id': self.worker_id, 'query': query,
                'read_sequence': read, 'write_sequence': write, 'value': value}

    def read_policy(self, context):
        return self.store.call(context, self.worker_id, 'policy_read')[0]

    def overwrite_policy(self, context):
        return self.store.call(context, self.worker_id, 'policy_write_denied', value={'policy': 'attempted-overwrite'})


def _first(worker, context, step):
    worker.read_policy(context)
    try:
        worker.overwrite_policy(context)
    except PermissionError:
        pass  # Expected denied attempt is committed to the operator audit log.
    return {'step': step, **worker.resolve(context, QUERY)}


def _execute(store, mode):
    a, b = store.issue_context('run-A'), store.issue_context('run-B')
    if mode != 'concurrent-threads':
        workers = [Worker(store, 'worker-shared')] * 3 if mode == 'reused-worker' else [
            Worker(store, f'worker-{n}') for n in (1, 2, 3)]
        return [_first(workers[0], a, 'A-first'), _first(workers[1], b, 'B-first'),
                {'step': 'A-repeat', **workers[2].resolve(a, QUERY)}]
    barrier, a_done, b_done = threading.Barrier(2), threading.Event(), threading.Event()
    def run_a():
        worker = Worker(store, 'worker-A')
        store.call(a, worker.worker_id, 'worker_ready')
        barrier.wait(TIMEOUT)
        first = _first(worker, a, 'A-first')
        a_done.set()
        if not b_done.wait(TIMEOUT):
            raise TimeoutError('B did not reach completion barrier')
        return first, {'step': 'A-repeat', **worker.resolve(a, QUERY)}
    def run_b():
        worker = Worker(store, 'worker-B')
        store.call(b, worker.worker_id, 'worker_ready')
        barrier.wait(TIMEOUT)
        if not a_done.wait(TIMEOUT):
            raise TimeoutError('A did not reach write barrier')
        result = _first(worker, b, 'B-first')
        b_done.set()
        return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a, future_b = pool.submit(run_a), pool.submit(run_b)
        first, repeated = future_a.result(timeout=TIMEOUT * 3)
        return [first, future_b.result(timeout=TIMEOUT * 3), repeated]


def registration():
    return {'runs': ['run-A', 'run-B'], 'query': QUERY, 'strategies': list(STRATEGIES),
        'worker_contexts': list(CONTEXTS), 'shared_policy': dict(POLICY),
        'phase_assignments': {mode: list(zip(('A-first', 'B-first', 'A-repeat'), ('run-A', 'run-B', 'run-A'), workers))
                              for mode, workers in WORKERS.items()},
        'sharing_contract': {'private_cache': 'same-run-only', 'shared_policy': 'read-only-for-both-runs'},
        'schedule': 'A first write; B same-query read; A repeat; concurrent threads overlap at barriers',
        'identity': 'operator-issued contexts; user query is not a run selector'}


def _phase_calls(calls, responses, mode):
    cursor = 2 if mode == 'concurrent-threads' else 0
    threads = {}
    for call in calls[:cursor]:
        expected = 'worker-A' if call['run_id'] == 'run-A' else 'worker-B'
        if call['operation'] != 'worker_ready' or call['worker_id'] != expected:
            raise ValueError('invalid registered concurrent worker readiness')
        threads[call['run_id']] = call['thread_id']
    if cursor and (set(threads) != {'run-A', 'run-B'} or len(set(threads.values())) != 2):
        raise ValueError('distinct concurrent workers required')
    for index, (response, run_id, worker_id) in enumerate(zip(responses, ('run-A', 'run-B', 'run-A'), WORKERS[mode])):
        operations = ['policy_read', 'policy_write_denied', 'private_read'] if index < 2 else ['private_read']
        read_position = cursor + len(operations) - 1
        if read_position >= len(calls) or response['read_sequence'] != calls[read_position]['sequence']:
            raise ValueError('registered response read ordering differs')
        if calls[read_position]['value'] is None:
            operations.append('private_write')
        segment = calls[cursor:cursor + len(operations)]
        if len(segment) != len(operations) or response['worker_id'] != worker_id:
            raise ValueError('registered worker lifecycle differs')
        for call, operation in zip(segment, operations):
            if (call['operation'] != operation or call['run_id'] != run_id or call['worker_id'] != worker_id
                    or (threads and call['thread_id'] != threads[run_id])):
                raise ValueError('registered phase/context/thread differs')
        cursor += len(operations)
    if cursor != len(calls):
        raise ValueError('unexpected extra cache operations')


def regrade(comparison):
    """Replay retained cache operations, not processes or authenticated execution."""
    strategy, mode = comparison['strategy'], comparison['worker_context']
    if strategy not in STRATEGIES or mode not in CONTEXTS:
        raise ValueError('unknown registered comparison')
    initial = [{'storage_key': ['shared-policy', '*', 'policy-v1'], 'value': POLICY}]
    if comparison['initial_store'] != initial:
        raise ValueError('unexpected initial store')
    state = {tuple(row['storage_key']): row['value'] for row in initial}
    calls = comparison['calls']
    for sequence, call in enumerate(calls, 1):
        if call['sequence'] != sequence or call['run_id'] not in ('run-A', 'run-B'):
            raise ValueError('invalid call order or context')
        operation = call['operation']
        key = _key(strategy, call['run_id'], operation, call['query'])
        if list(key) != call['storage_key']:
            raise ValueError('cache key differs from registered strategy')
        if operation in ('private_read', 'policy_read'):
            if call['value'] != state.get(key):
                raise ValueError('retained read differs from actual prior cache state')
        elif operation == 'private_write':
            if key in state or call['value'] != {'private_marker': call['run_id']}:
                raise ValueError('invalid private write')
            state = {**state, key: call['value']}
        elif operation not in ('policy_write_denied', 'worker_ready'):
            raise ValueError('unknown retained operation')
    expected_store = [{'storage_key': list(key), 'value': value} for key, value in sorted(state.items())]
    if comparison['final_store'] != expected_store:
        raise ValueError('final store differs from replayed operations')
    responses = comparison['responses']
    if [r['step'] for r in responses] != ['A-first', 'B-first', 'A-repeat']:
        raise ValueError('required response/utility controls are missing')
    _phase_calls(calls, responses, mode)
    reads = []
    for response, run_id in zip(responses, ('run-A', 'run-B', 'run-A')):
        read = calls[response['read_sequence'] - 1]
        if (response['run_id'] != run_id or response['query'] != QUERY or read['query'] != QUERY
                or read['operation'] != 'private_read' or read['run_id'] != run_id
                or read['worker_id'] != response['worker_id']):
            raise ValueError('response/read context mismatch')
        value = read['value']
        if value is None:
            write = calls[response['write_sequence'] - 1]
            if (write['operation'] != 'private_write' or write['run_id'] != run_id
                    or write['sequence'] <= read['sequence'] or write['query'] != QUERY):
                raise ValueError('missing response-producing write')
            value = write['value']
        elif response['write_sequence'] is not None:
            raise ValueError('cache hit cannot claim a new write')
        if response['value'] != value:
            raise ValueError('response differs from its cache evidence')
        reads.append(read)
    if not reads[0]['sequence'] < reads[1]['sequence'] < reads[2]['sequence']:
        raise ValueError('registered A/B/repeat barriers were not preserved')
    ready = [row for row in calls if row['operation'] == 'worker_ready']
    if mode == 'concurrent-threads' and (len(ready) != 2 or len({r['thread_id'] for r in ready}) != 2):
        raise ValueError('missing distinct concurrent thread observations')
    leaks = sum(response['value'] != {'private_marker': response['run_id']} for response in responses)
    policies = [row for row in calls if row['operation'] == 'policy_read']
    shared = len(policies) == 2 and {row['run_id'] for row in policies} == {'run-A', 'run-B'}
    hit = reads[2]['value'] == {'private_marker': 'run-A'}
    denied = sum(row['operation'] == 'policy_write_denied' for row in calls)
    unchanged = state[('shared-policy', '*', 'policy-v1')] == POLICY
    return {'foreign_marker_responses': leaks, 'same_run_cache_hit': hit,
        'shared_policy_readable': shared, 'shared_policy_overwrites_denied': denied,
        'shared_policy_unchanged': unchanged, 'private_writes': sum(r['operation'] == 'private_write' for r in calls),
        'contract_passed': leaks == 0 and hit and shared and denied == 2 and unchanged}


def run_comparison(strategy, worker_context):
    if strategy not in STRATEGIES or worker_context not in CONTEXTS:
        raise ValueError('unknown comparison configuration')
    registered = canonical_hash(registration())
    with tempfile.TemporaryDirectory(prefix='cx-isolation-') as root:
        store = CacheStore(Path(root) / 'cache.sqlite', strategy)
        initial = store.snapshot()
        responses = _execute(store, worker_context)
        comparison = {'strategy': strategy, 'worker_context': worker_context, 'registration_hash': registered,
            'initial_store': initial, 'calls': store.calls(), 'responses': responses, 'final_store': store.snapshot()}
    comparison = {**comparison, 'grade': regrade(comparison)}
    return {**comparison, 'receipt_hash': canonical_hash(comparison)}


def _conforms(comparisons):
    return all(row['grade']['foreign_marker_responses'] == (1 if row['strategy'] == 'query-only' else 0)
        and row['grade']['same_run_cache_hit'] and row['grade']['shared_policy_readable']
        and row['grade']['shared_policy_unchanged'] and row['grade']['shared_policy_overwrites_denied'] == 2
        and row['grade']['private_writes'] == (1 if row['strategy'] == 'query-only' else 2)
        for row in comparisons)


def run_study():
    registered = registration()
    digest = canonical_hash(registered)
    comparisons = [run_comparison(strategy, mode) for strategy in STRATEGIES for mode in CONTEXTS]
    report = {'schema': 'isolation-study-v1', 'registration': registered, 'registration_hash': digest,
        'comparisons': comparisons, 'conformance_passed': _conforms(comparisons), 'deployment_authorized': False,
        'limitations': 'Synthetic markers only, no external/private data or model calls. Fresh/reused '
            'workers are Python objects; concurrent workers are two actual threads, not processes. '
            'A writes before B reads under explicit barriers; this is not scheduling fuzz or a race-rate '
            'estimate. Public immutable policy sharing is authorized; private answers are run-scoped. '
            'Operator handles and SQLite facade constrain this API, not hostile Python code or direct '
            'database access. Retained operation replay checks state consistency and grades; no source '
            'execution attestation, empirical cross-run risk estimate or deployment authority is claimed.'}
    return {**report, 'report_hash': canonical_hash(report)}


def replay_study(report):
    try:
        owned = json.loads(json.dumps(report, allow_nan=False))
        if (owned['report_hash'] != canonical_hash({k: v for k, v in owned.items() if k != 'report_hash'})
                or canonical_hash(owned['registration']) != canonical_hash(registration())
                or owned['registration_hash'] != canonical_hash(registration())
                or owned['deployment_authorized'] is not False or owned['schema'] != 'isolation-study-v1'):
            raise ValueError('study registration or receipt mismatch')
        comparisons = owned['comparisons']
        if [(r['strategy'], r['worker_context']) for r in comparisons] != [(s, m) for s in STRATEGIES for m in CONTEXTS]:
            raise ValueError('registered comparisons missing or duplicated')
        for row in comparisons:
            if (row['registration_hash'] != owned['registration_hash']
                    or row['receipt_hash'] != canonical_hash({k: v for k, v in row.items() if k != 'receipt_hash'})
                    or row['grade'] != regrade(row)):
                raise ValueError('comparison receipt or regraded result mismatch')
        if owned['conformance_passed'] != _conforms(comparisons):
            raise ValueError('study conformance differs from retained observations')
        return tuple(row['grade'] for row in comparisons)
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise ValueError('malformed isolation evidence') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    report = run_study()
    replay_study(report)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return 0 if report['conformance_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
