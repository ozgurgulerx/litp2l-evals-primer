"""Immutable local window selection, not attempt recovery or controller authority.

The trusted caller supplies a manifest digest; equality does not authenticate it.
Campaign identity is local path/device/inode/policy, not portable provenance.
Registration precedes agent work but is not atomic with later effect transactions.
"""

import json
import re
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path

from cx_eval_lab.durable_completion import _binding, _hash, _json, _namespace
from cx_eval_lab.exposure_control import ExposureState
from cx_eval_lab.exposure_study import build_window_plan


def _validate(plan):
    """Exact canonical equality also rejects bool/int aliases and extra fields."""
    if not isinstance(plan, dict):
        raise TypeError('window plan must be an object')
    try:
        _namespace(plan['execution_namespace'])
        digest = plan['manifest_digest']
        if not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None:
            raise ValueError('explicit SHA-256 manifest digest required')
        if plan['effect_backend'] != 'durable':
            raise ValueError('registered window requires durable effects')
        expected = build_window_plan(ExposureState(**plan['predecessor']), plan['number'],
            plan['fault_mode'], immature=plan['immature'], execution_namespace=plan['execution_namespace'],
            manifest_digest=digest, effect_backend='durable')
        serialized = _json(plan)
        if serialized != _json(expected):
            raise ValueError('window plan does not match fixed study selection')
        return serialized
    except (KeyError, TypeError) as error:
        raise ValueError('invalid window plan structure') from error


@dataclass(frozen=True)
class WindowRegistry:
    """Immutable registration only. Re-execution is not safe window resumption."""

    path: Path
    campaign: object
    binding: str

    @classmethod
    def initialize(cls, path, campaign):
        registry = cls(Path(path).absolute(), campaign, _binding(campaign))
        if registry.path.exists() or registry.path.is_symlink():
            raise ValueError('window registry already exists')
        registry.path.parent.mkdir(parents=True, exist_ok=True)
        with registry.path.open('xb'):
            pass
        with closing(registry._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('PRAGMA user_version=1')
            db.execute('CREATE TABLE identity (binding TEXT NOT NULL)')
            db.execute('INSERT INTO identity VALUES (?)', (registry.binding,))
            db.execute('CREATE TABLE windows (namespace TEXT NOT NULL, number INTEGER NOT NULL, '
                       'plan TEXT NOT NULL, plan_hash TEXT NOT NULL, PRIMARY KEY(namespace,number))')
        return registry

    @classmethod
    def open(cls, path, campaign):
        registry = cls(Path(path).absolute(), campaign, _binding(campaign))
        with registry._transaction():
            pass
        return registry

    def require_campaign(self, campaign):
        if _binding(campaign) != self.binding:
            raise ValueError('window registry campaign binding mismatch')

    def _connect(self):
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError('existing regular window registry required')
        db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        return db

    @contextmanager
    def _transaction(self, *, write=False):
        self.require_campaign(self.campaign)
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('window registry schema mismatch')
            identities = db.execute('SELECT binding FROM identity').fetchall()
            if len(identities) != 1 or identities[0][0] != self.binding:
                raise ValueError('window registry identity mismatch')
            yield db

    def _read(self, row):
        serialized = row['plan']
        if not isinstance(serialized, str) or _hash(serialized) != row['plan_hash']:
            raise ValueError('window plan hash mismatch')
        plan = json.loads(serialized)
        if (_validate(plan) != serialized or plan['execution_namespace'] != row['namespace']
                or type(plan['number']) is not int or plan['number'] != row['number']):
            raise ValueError('window plan identity or canonical encoding mismatch')
        return plan

    def register(self, plan):
        serialized = _validate(plan)
        namespace, number = plan['execution_namespace'], plan['number']
        with self._transaction(write=True) as db:
            row = db.execute('SELECT * FROM windows WHERE namespace=? AND number=?',
                             (namespace, number)).fetchone()
            if row is not None:
                saved = self._read(row)
                if row['plan'] != serialized:
                    raise ValueError('window registration conflict')
                return saved
            db.execute('INSERT INTO windows VALUES (?, ?, ?, ?)',
                       (namespace, number, serialized, _hash(serialized)))
        return json.loads(serialized)

    def inspect(self, namespace, number):
        _namespace(namespace)
        if type(number) is not int or number <= 0:
            raise ValueError('positive integer window number required')
        with self._transaction() as db:
            row = db.execute('SELECT * FROM windows WHERE namespace=? AND number=?',
                             (namespace, number)).fetchone()
            return None if row is None else self._read(row)
