"""Atomic receipts for the existing local exposure state machine.

Caller-supplied observations remain trusted inputs, not qualified evidence.
This database does not fence agent actions or grant deployment authority.
"""

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from cx_eval_lab.exposure_control import ExposureState, ExposureWindow, transition


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _source():
    root = Path(__file__).parent
    return _hash(_encode({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                         for name in ('durable_controller.py', 'exposure_control.py')}))


@dataclass(frozen=True)
class DurableController:
    path: Path

    @classmethod
    def initialize(cls, path, state):
        if not isinstance(state, ExposureState):
            raise TypeError('validated initial exposure state required')
        controller = cls(Path(path).absolute())
        if controller.path.exists() or controller.path.is_symlink():
            raise ValueError('controller database already exists')
        payload = _encode(asdict(state))
        controller.path.parent.mkdir(parents=True, exist_ok=True)
        with controller.path.open('xb'):
            pass
        with closing(controller._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('PRAGMA user_version=1')
            db.execute('CREATE TABLE controller (id INTEGER PRIMARY KEY CHECK(id=1), '
                       'source TEXT NOT NULL, state TEXT NOT NULL, state_hash TEXT NOT NULL)')
            db.execute('INSERT INTO controller VALUES (1, ?, ?, ?)', (_source(), payload, _hash(payload)))
            db.execute('CREATE TABLE receipts (identity TEXT PRIMARY KEY, inputs TEXT NOT NULL, '
                       'receipt TEXT NOT NULL, receipt_hash TEXT NOT NULL)')
        return controller

    @classmethod
    def open(cls, path):
        controller = cls(Path(path).absolute())
        controller.state()
        return controller

    def _connect(self):
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError('existing regular controller database required')
        db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        return db

    @contextmanager
    def _transaction(self, *, write=False):
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('controller schema mismatch')
            rows = db.execute('SELECT * FROM controller').fetchall()
            if len(rows) != 1 or rows[0]['source'] != _source():
                raise ValueError('controller source identity mismatch')
            row = rows[0]
            if _hash(row['state']) != row['state_hash']:
                raise ValueError('controller state hash mismatch')
            state = ExposureState(**json.loads(row['state']))
            if _encode(asdict(state)) != row['state']:
                raise ValueError('noncanonical controller state')
            yield db, state

    def state(self):
        with self._transaction() as (_, state):
            return state

    def apply(self, identity, expected, window, *, now, resume=False):
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError('nonempty decision identity required')
        if not isinstance(expected, ExposureState) or not isinstance(window, ExposureWindow):
            raise TypeError('validated predecessor and window required')
        if type(now) is not int or now < 0 or type(resume) is not bool:
            raise ValueError('nonnegative integer time and boolean resume required')
        inputs = _encode({'predecessor': asdict(expected), 'window': asdict(window),
                          'now': now, 'resume': resume})
        with self._transaction(write=True) as (db, current):
            saved = db.execute('SELECT * FROM receipts WHERE identity=?', (identity,)).fetchone()
            if saved is not None:
                if saved['inputs'] != inputs:
                    raise ValueError('decision identity conflict')
                if _hash(saved['receipt']) != saved['receipt_hash']:
                    raise ValueError('decision receipt hash mismatch')
                receipt = json.loads(saved['receipt'])
                if (_encode(receipt) != saved['receipt'] or receipt['identity'] != identity
                        or _encode(receipt['inputs']) != inputs):
                    raise ValueError('decision receipt binding mismatch')
                return receipt
            if _encode(asdict(current)) != _encode(asdict(expected)):
                raise ValueError('controller predecessor conflict')
            decision = transition(current, window, now=now, resume=resume)
            receipt = {'identity': identity, 'inputs': json.loads(inputs), 'decision': asdict(decision),
                       'authority': 'simulation_only', 'evidence_qualification': 'caller_owned'}
            serialized, next_state = _encode(receipt), _encode(asdict(decision.state))
            db.execute('INSERT INTO receipts VALUES (?, ?, ?, ?)',
                       (identity, inputs, serialized, _hash(serialized)))
            db.execute('UPDATE controller SET state=?, state_hash=? WHERE id=1',
                       (next_state, _hash(next_state)))
        return json.loads(serialized)
