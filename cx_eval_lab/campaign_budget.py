"""Local SQLite estimated-cost admission, not a provider invoice ceiling.

Use an operator-owned local directory. Unknown and interrupted calls retain
their reservations. Existing invocation IDs never authorize another dispatch.
No reconciliation, provider cancellation, or distributed database is implied.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Callable

from cx_eval_lab.evidence import canonical_hash


MAX_MONEY = 10**12  # Teaching ledger numeric boundary, micro-USD, not a price.


def _integer(value, minimum=0, maximum=MAX_MONEY):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('expected a bounded integer')
    return value


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,256}', value):
        raise ValueError('explicit non-sensitive identifier required')
    return value


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
        raise ValueError('SHA-256 identity required')


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def usd_to_micro(value):
    """Round estimates upward; unknown is not zero."""
    if value is None:
        return None
    if type(value) not in (int, float):
        raise ValueError('cost must be a finite nonnegative number or unknown')
    amount = Decimal(str(value))
    if not amount.is_finite() or not 0 <= amount <= MAX_MONEY / 1_000_000:
        raise ValueError('cost outside the ledger numeric boundary')
    numerator, denominator = amount.as_integer_ratio()
    return (numerator * 1_000_000 + denominator - 1) // denominator


@dataclass(frozen=True)
class CampaignPolicy:
    campaign_id: str
    max_estimated_micro_usd: int
    max_admissions: int
    deadline_unix_ms: int
    reservation_micro_usd: int

    def __post_init__(self):
        _identifier(self.campaign_id)
        _integer(self.max_estimated_micro_usd, 1)
        _integer(self.max_admissions, 1, 1_000_000)
        _integer(self.deadline_unix_ms, 1, 2**53)
        _integer(self.reservation_micro_usd, 1, self.max_estimated_micro_usd)

    @property
    def content_hash(self):
        return canonical_hash({'schema': 'judge-campaign-policy-v1', **asdict(self)})


@dataclass(frozen=True)
class Admission:
    admitted: bool
    reason: str
    invocation_id: str
    campaign_policy_hash: str


@dataclass(frozen=True)
class CampaignLedger:
    path: Path
    policy: CampaignPolicy
    clock_ms: Callable[[], int] = field(default=lambda: time.time_ns() // 1_000_000,
                                      repr=False, compare=False)

    @classmethod
    def create(cls, path, policy, **kwargs):
        if not isinstance(policy, CampaignPolicy):
            raise ValueError('validated campaign policy required')
        path = Path(path).absolute()
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        # Initialization failures leave a visible incomplete file; never reset it.
        with sqlite3.connect(path) as connection:
            connection.execute('CREATE TABLE campaign (policy_json TEXT NOT NULL, '
                               'last_seen_ms INTEGER NOT NULL, halt_reason TEXT)')
            connection.execute('INSERT INTO campaign VALUES (?, 0, NULL)', (_json(asdict(policy)),))
            connection.execute('CREATE TABLE invocations (id TEXT PRIMARY KEY, '
                               'request_hash TEXT NOT NULL, configuration_hash TEXT NOT NULL, '
                               'reserved_micro INTEGER NOT NULL, admitted_ms INTEGER NOT NULL, '
                               'state TEXT NOT NULL, estimate_micro INTEGER, judgment_json TEXT, '
                               'receipt_json TEXT)')
        return cls.open(path, policy, **kwargs)

    @classmethod
    def open(cls, path, policy, **kwargs):
        ledger = cls(Path(path).absolute(), policy, **kwargs)
        with ledger._transaction():
            pass
        return ledger

    @contextmanager
    def _transaction(self):
        if not isinstance(self.policy, CampaignPolicy) or self.path.is_symlink() or not self.path.is_file():
            raise ValueError('existing regular operator-owned ledger required')
        connection = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('BEGIN IMMEDIATE')
            rows = connection.execute('SELECT * FROM campaign').fetchall()
            if len(rows) != 1 or rows[0]['policy_json'] != _json(asdict(self.policy)):
                raise ValueError('campaign policy mismatch; cannot reset existing ledger')
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _time_and_halt(self, connection):
        now = _integer(self.clock_ms(), 0, 2**53)
        campaign = connection.execute('SELECT * FROM campaign').fetchone()
        reason = campaign['halt_reason']
        if now < campaign['last_seen_ms']:
            reason = reason or 'clock_regression'
        elif now >= self.policy.deadline_unix_ms:
            reason = reason or 'deadline_reached'
        connection.execute('UPDATE campaign SET last_seen_ms=?, halt_reason=?',
                           (max(now, campaign['last_seen_ms']), reason))
        return now, reason

    def reserve(self, invocation_id, request_hash, configuration_hash):
        _identifier(invocation_id)
        _digest(request_hash)
        _digest(configuration_hash)
        with self._transaction() as connection:
            prior = connection.execute('SELECT * FROM invocations WHERE id=?', (invocation_id,)).fetchone()
            if prior:
                if prior['request_hash'] != request_hash or prior['configuration_hash'] != configuration_hash:
                    raise ValueError('invocation identity reused with changed evidence or configuration')
                return Admission(False, 'invocation_already_reserved', invocation_id, self.policy.content_hash)
            now, reason = self._time_and_halt(connection)
            rows = connection.execute('SELECT * FROM invocations').fetchall()
            occupied = sum(r['estimate_micro'] if r['state'] == 'known' else r['reserved_micro'] for r in rows)
            if not reason and len(rows) >= self.policy.max_admissions:
                reason = 'admission_limit_reached'
            if not reason and occupied + self.policy.reservation_micro_usd > self.policy.max_estimated_micro_usd:
                reason = 'estimated_budget_exhausted'
            if reason:
                return Admission(False, reason, invocation_id, self.policy.content_hash)
            connection.execute('INSERT INTO invocations VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL)',
                               (invocation_id, request_hash, configuration_hash,
                                self.policy.reservation_micro_usd, now, 'reserved'))
            return Admission(True, 'reserved', invocation_id, self.policy.content_hash)

    def finalize(self, invocation_id, estimate_micro_usd, judgment_json):
        _identifier(invocation_id)
        if estimate_micro_usd is not None:
            _integer(estimate_micro_usd)
        if not isinstance(judgment_json, str) or len(judgment_json.encode('utf-8')) > 2_000_000:
            raise ValueError('bounded retained judgment JSON required')
        judgment = json.loads(judgment_json)
        if not isinstance(judgment, dict):
            raise ValueError('judgment must be a JSON object')
        retained = _json(judgment)
        with self._transaction() as connection:
            row = connection.execute('SELECT * FROM invocations WHERE id=?', (invocation_id,)).fetchone()
            if row is None:
                raise ValueError('cannot finalize an unreserved invocation')
            if row['state'] != 'reserved':
                if row['estimate_micro'] != estimate_micro_usd or row['judgment_json'] != retained:
                    raise ValueError('conflicting finalization cannot overwrite retained evidence')
                return json.loads(row['receipt_json'])
            now, _ = self._time_and_halt(connection)
            overrun = estimate_micro_usd is not None and estimate_micro_usd > row['reserved_micro']
            receipt = {'schema': 'judge-campaign-receipt-v1', 'invocation_id': invocation_id,
                       'campaign_policy_hash': self.policy.content_hash,
                       'request_hash': row['request_hash'], 'configuration_hash': row['configuration_hash'],
                       'reserved_micro_usd': row['reserved_micro'], 'estimate_micro_usd': estimate_micro_usd,
                       'state': 'unknown' if estimate_micro_usd is None else 'known',
                       'judgment_hash': canonical_hash(judgment), 'completed_unix_ms': now,
                       'reservation_overrun': overrun,
                       'completed_after_deadline': now >= self.policy.deadline_unix_ms}
            connection.execute('UPDATE invocations SET state=?, estimate_micro=?, judgment_json=?, '
                               'receipt_json=? WHERE id=?',
                               (receipt['state'], estimate_micro_usd, retained, _json(receipt), invocation_id))
            if overrun:
                connection.execute('UPDATE campaign SET halt_reason=?', ('reservation_overrun',))
            return receipt

    def snapshot(self):
        with self._transaction() as connection:
            rows = connection.execute('SELECT * FROM invocations ORDER BY id').fetchall()
            halt = connection.execute('SELECT halt_reason FROM campaign').fetchone()[0]
            known = sum(r['estimate_micro'] for r in rows if r['state'] == 'known')
            held = sum(r['reserved_micro'] for r in rows if r['state'] != 'known')
            unknown = sum(r['state'] != 'known' for r in rows)
            return {'schema': 'judge-campaign-snapshot-v1', 'policy': asdict(self.policy),
                    'policy_hash': self.policy.content_hash, 'admissions': len(rows),
                    'known_estimate_micro_usd': known, 'held_reservations_micro_usd': held,
                    'committed_micro_usd': known + held, 'unknown_or_pending_invocations': unknown,
                    'complete_estimate_micro_usd': None if unknown else known,
                    'halt_reason': halt, 'deployment_authorized': False,
                    'cost_scope': 'judge token estimates only; not invoices or total operating cost',
                    'invocations': [dict(row) for row in rows]}
