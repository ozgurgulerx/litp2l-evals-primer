"""Barrier-ordered local containment, cooperative workers and synthetic effects only."""

import argparse
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import select
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

from cx_eval_lab.evidence import canonical_hash

TIMEOUT = 5
CASES = {
    'early-revoke': ('protected', False, 'early'),
    'late-revoke': ('protected', False, 'late'),
    'cancel-parent-only': ('protected', True, 'parent-only'),
    'cancel-parent-and-revoke': ('protected', True, 'parent-global'),
    'false-positive': ('legitimate', False, 'early'),
    'normal': ('legitimate', False, 'normal'),
}


def _db(path):
    db = sqlite3.connect(path, timeout=TIMEOUT)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA synchronous=FULL')
    return db


def initialize(path):
    if Path(path).exists():
        raise ValueError('use a new isolated database')
    with closing(_db(path)) as db, db:
        db.execute('CREATE TABLE authority (revoked INTEGER NOT NULL)')
        db.execute('INSERT INTO authority VALUES (0)')
        db.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, actor TEXT, pid INTEGER, '
                   'event TEXT, request_id TEXT, details TEXT)')
        db.execute('CREATE TABLE effects (request_id TEXT PRIMARY KEY, kind TEXT, worker_pid INTEGER, '
                   'commit_sequence INTEGER NOT NULL)')


def _event(db, event, *, actor='controller', request_id=None, details=None):
    return db.execute('INSERT INTO events(actor,pid,event,request_id,details) VALUES (?,?,?,?,?)',
        (actor, os.getpid(), event, request_id, json.dumps(details, allow_nan=False))).lastrowid


def _record(path, event, details=None):
    with closing(_db(path)) as db, db:
        _event(db, event, details=details)


def revoke(path):
    with closing(_db(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE authority SET revoked=1')
        _event(db, 'authority_revoked')


def attempt_write(path, request_id, kind):
    if request_id not in ('request-1', 'request-2') or kind not in ('protected', 'legitimate'):
        raise ValueError('unknown synthetic request')
    with closing(_db(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        _event(db, 'write_attempted', actor='worker', request_id=request_id)
        revoked = db.execute('SELECT revoked FROM authority').fetchone()[0]
        if revoked:
            _event(db, 'write_denied', actor='worker', request_id=request_id)
            return {'status': 'denied', 'request_id': request_id}
        sequence = _event(db, 'write_committed', actor='worker', request_id=request_id)
        db.execute('INSERT INTO effects VALUES (?,?,?,?)', (request_id, kind, os.getpid(), sequence))
    return {'status': 'committed', 'request_id': request_id}


def snapshot(path):
    with closing(_db(path)) as db:
        return {'revoked': bool(db.execute('SELECT revoked FROM authority').fetchone()[0]),
                'effects': [dict(row) for row in db.execute('SELECT * FROM effects ORDER BY commit_sequence')],
                'events': [{**dict(row), 'details': json.loads(row['details'])}
                           for row in db.execute('SELECT * FROM events ORDER BY seq')]}


def _send(channel, value):
    channel.sendall((json.dumps(value, allow_nan=False) + '\n').encode())


def _receive(channel):
    deadline, data = time.monotonic() + TIMEOUT, bytearray()
    while len(data) < 16_384:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('IPC deadline exceeded')
        channel.settimeout(remaining)
        byte = channel.recv(1)
        if not byte:
            raise EOFError('worker IPC closed')
        if byte == b'\n':
            return json.loads(data)
        data.extend(byte)
    raise ValueError('oversized worker IPC message')


def _worker(path, descriptor, kind):
    with socket.socket(fileno=descriptor) as channel:
        with closing(_db(path)) as db, db:
            _event(db, 'work_queued', actor='worker', request_id='request-1')
        _send(channel, {'event': 'queued', 'pid': os.getpid(), 'request_id': 'request-1'})
        while True:
            message = _receive(channel)
            if message == {'command': 'shutdown'}:
                return 0
            if message.get('command') != 'attempt':
                raise ValueError('unknown worker command')
            result = attempt_write(path, message.get('request_id'), kind)
            _send(channel, {**result, 'pid': os.getpid()})


def _command(path, descriptor, kind, role):
    return [sys.executable, '-m', 'cx_eval_lab.containment_study', role,
            '--database', str(path), '--channel-fd', str(descriptor), '--kind', kind]


def _coordinator(path, descriptor, kind):
    child = subprocess.Popen(_command(path, descriptor, kind, '--worker'), pass_fds=(descriptor,),
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(descriptor)
    try:
        print(json.dumps({'event': 'coordinator_ready', 'pid': os.getpid(), 'child_pid': child.pid}), flush=True)
        for line in sys.stdin:
            if line.strip() == 'cancel':
                # Task cancellation stops this coordinator's work; its already queued
                # child has separate authority and direct controller-owned IPC.
                print(json.dumps({'event': 'parent_task_cancelled', 'pid': os.getpid()}), flush=True)
            elif line.strip() == 'reap':
                child.wait(timeout=TIMEOUT)
                break
            else:
                raise ValueError('unknown coordinator command')
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=TIMEOUT)
        print(json.dumps({'event': 'child_reaped', 'pid': child.pid, 'returncode': child.returncode}), flush=True)
    return 0 if child.returncode == 0 else 2


def _read_process(process):
    if not select.select([process.stdout], [], [], TIMEOUT)[0]:
        raise TimeoutError('coordinator acknowledgement deadline exceeded')
    return json.loads(process.stdout.readline(16_384))


@contextmanager
def _owned_worker(path, kind, delegated):
    controller, endpoint = socket.socketpair()
    process = None
    processes = []
    try:
        role = '--coordinator' if delegated else '--worker'
        process = subprocess.Popen(_command(path, endpoint.fileno(), kind, role),
            pass_fds=(endpoint.fileno(),), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, start_new_session=True)
        endpoint.close()
        ready = _read_process(process) if delegated else {'pid': process.pid}
        yield controller, process, ready.get('child_pid', process.pid), processes
    finally:
        endpoint.close()
        try:
            _send(controller, {'command': 'shutdown'})
        except OSError:
            pass
        controller.close()
        if process is not None:
            try:
                output, _ = process.communicate('reap\n' if delegated else None, timeout=TIMEOUT * 3)
                if delegated:
                    acknowledgements = [json.loads(line) for line in output.splitlines()]
                    processes.extend({'role': 'worker', 'pid': item['pid'], 'returncode': item['returncode']}
                                     for item in acknowledgements if item.get('event') == 'child_reaped')
            except subprocess.TimeoutExpired:
                # This process group was created by this trial, never a user process group.
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=TIMEOUT)
                raise TimeoutError('owned process cleanup exceeded deadline')
            finally:
                processes.insert(0, {'role': 'coordinator' if delegated else 'worker',
                                     'pid': process.pid, 'returncode': process.returncode})


def _request(path, channel, request_id):
    _record(path, 'release_barrier', {'request_id': request_id})
    _send(channel, {'command': 'attempt', 'request_id': request_id})
    result = _receive(channel)
    if result.get('request_id') != request_id or result.get('status') not in ('denied', 'committed'):
        raise ValueError('unexpected worker acknowledgement')
    _record(path, 'worker_acknowledged', result)


def grade(state, kind):
    events, effects = state['events'], state['effects']
    revocations = [row['seq'] for row in events if row['event'] == 'authority_revoked']
    cancellations = [row['seq'] for row in events if row['event'] == 'parent_task_cancelled']
    return {'attempts': sum(row['event'] == 'write_attempted' for row in events),
        'denied_attempts': sum(row['event'] == 'write_denied' for row in events),
        'completed_effects': len(effects),
        'prohibited_effect_prevented': not effects if kind == 'protected' else None,
        'benign_task_completed': bool(effects) if kind == 'legitimate' else None,
        'effects_before_revocation': sum(row['commit_sequence'] < revocations[0] for row in effects)
                                     if revocations else None,
        'effects_after_revocation': sum(row['commit_sequence'] > revocations[0] for row in effects)
                                    if revocations else None,
        'effects_after_parent_cancel': sum(row['commit_sequence'] > cancellations[0] for row in effects)
                                       if cancellations else 0}


def run_trial(case):
    if case not in CASES:
        raise ValueError('unknown containment control')
    kind, delegated, schedule = CASES[case]
    with tempfile.TemporaryDirectory(prefix='cx-containment-') as root:
        path = Path(root) / 'synthetic.sqlite'
        initialize(path)
        with _owned_worker(path, kind, delegated) as (channel, process, worker_pid, processes):
            queued = _receive(channel)
            if queued != {'event': 'queued', 'pid': worker_pid, 'request_id': 'request-1'}:
                raise ValueError('worker did not acknowledge queued work')
            _record(path, 'queue_acknowledged', queued)
            if schedule == 'late':
                _request(path, channel, 'request-1')
            if schedule != 'normal':
                _record(path, 'scripted_detector_alert', {'reference_kind': kind})
            if delegated:
                process.stdin.write('cancel\n')
                process.stdin.flush()
                cancelled = _read_process(process)
                if cancelled != {'event': 'parent_task_cancelled', 'pid': process.pid}:
                    raise ValueError('coordinator cancellation acknowledgement mismatch')
                _record(path, 'parent_task_cancelled', cancelled)
            if schedule in ('early', 'late', 'parent-global'):
                revoke(path)
            if schedule != 'late':
                _request(path, channel, 'request-1')
            if schedule in ('early', 'late', 'parent-global'):
                _request(path, channel, 'request-2')
        state = snapshot(path)
    trial = {'case': case, 'configuration': {'kind': kind, 'delegated': delegated, 'schedule': schedule},
             'processes': processes, 'final_state': state, 'grade': grade(state, kind)}
    return {**trial, 'artifact_hash': canonical_hash(trial)}


def run_study():
    registration = {'cases': CASES, 'ipc_timeout_seconds': TIMEOUT,
                    'ordering': 'acknowledged IPC barriers and SQLite transaction event sequences'}
    registration_hash = canonical_hash(registration)
    trials = [run_trial(case) for case in CASES]
    conforms = ([t['grade']['completed_effects'] for t in trials] == [0, 1, 1, 0, 0, 1]
        and [t['grade']['denied_attempts'] for t in trials] == [2, 1, 0, 2, 2, 0]
        and all(p['returncode'] == 0 for t in trials for p in t['processes'])
        and all(len(t['processes']) == (2 if t['configuration']['delegated'] else 1) for t in trials))
    return {'schema': 'containment-study-v1', 'deployment_authorized': False,
        'evidence_kind': 'executed_local_processes_and_sqlite', 'configuration': registration,
        'registration_hash': registration_hash, 'conformance_passed': conforms, 'trials': trials,
        'limitations': 'Scripted detector alerts and reference kinds, not measured detection accuracy. '
            'Coordinator task cancellation is acknowledged, not an OS-kill or process-tree kill test. '
            'The coordinator remains only to reap its independently controlled queued child. '
            'Cooperative workers use the guarded SQLite tool; they are not hostile code in a sandbox. '
            'Revocation and insertion share a serialized transaction boundary. Event sequences prove '
            'the scheduled order, not real-world latency or race probabilities. False stops and '
            'prevented prohibited effects are separate outcomes. All effects are synthetic temporary '
            'rows; no network, external data, paid calls or deployment authority. IPC and cleanup have '
            'bounded waits; no real detector, distributed revocation or production containment is qualified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--coordinator', action='store_true')
    parser.add_argument('--database', type=Path)
    parser.add_argument('--channel-fd', type=int)
    parser.add_argument('--kind', choices=('protected', 'legitimate'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.worker or args.coordinator:
        if args.database is None or not args.database.is_file() or args.channel_fd is None or args.kind is None:
            parser.error('worker requires initialized database, channel and synthetic kind')
        try:
            return (_worker if args.worker else _coordinator)(args.database, args.channel_fd, args.kind)
        except (OSError, EOFError, ValueError, subprocess.TimeoutExpired):
            return 2
    if args.output is None or args.output.exists():
        parser.error('choose a new output path')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return 0 if report['conformance_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
