"""Small durable mock payment boundary for the process-recovery experiment.

This uses real SQLite transactions but never moves real money. The payment
commit and workflow checkpoint deliberately occupy separate transactions.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys


OPERATION = "refund:order-recovery-001"
ORDER = "order-recovery-001"
AMOUNT = 4000
CURRENCY = "USD"
MAX_INTEGER = 2**63 - 1


def _validate_budget(max_actions, currency_caps):
    if (type(max_actions) is not int or not 0 <= max_actions <= MAX_INTEGER
            or not isinstance(currency_caps, dict)
            or any(currency not in {'USD', 'EUR', 'GBP'} or type(cap) is not int
                   or not 0 <= cap <= MAX_INTEGER for currency, cap in currency_caps.items())):
        raise ValueError('budget requires nonnegative int64 count and registered currency caps')


def connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA synchronous=FULL")
    return db


def initialize(path: Path, *, max_actions=None, currency_caps=None):
    """Register an immutable allowance for this dedicated DB, before any effects.

    No caller-selected campaign exists on issue_payment. The DB owner is trusted;
    direct database tampering is outside this local mock boundary.
    """
    if max_actions is not None or currency_caps is not None:
        _validate_budget(max_actions, currency_caps)
    if path.exists() or path.is_symlink():
        raise ValueError("recovery database already exists; use a new trial directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("CREATE TABLE approvals (order_id TEXT PRIMARY KEY, amount_cents INTEGER, currency TEXT, granted INTEGER)")
        db.execute("CREATE TABLE payments (idempotency_key TEXT PRIMARY KEY, order_id TEXT, amount_cents INTEGER, currency TEXT)")
        db.execute("CREATE TABLE checkpoints (operation TEXT PRIMARY KEY, status TEXT)")
        db.execute("INSERT INTO approvals VALUES (?, ?, ?, 1)", (ORDER, AMOUNT, CURRENCY))
        if max_actions is not None:
            db.execute('CREATE TABLE campaign_budget (singleton INTEGER PRIMARY KEY CHECK(singleton=1), max_actions INTEGER NOT NULL)')
            db.execute('CREATE TABLE campaign_currency_caps (currency TEXT PRIMARY KEY, max_cents INTEGER NOT NULL)')
            db.execute('INSERT INTO campaign_budget VALUES (1, ?)', (max_actions,))
            db.executemany('INSERT INTO campaign_currency_caps VALUES (?, ?)', sorted(currency_caps.items()))


def _budget_state(db):
    """Read only inside the caller's single read/write transaction."""
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='campaign_budget'").fetchone() is None:
        return None
    policy = db.execute('SELECT max_actions FROM campaign_budget WHERE singleton=1').fetchone()
    if policy is None:
        raise ValueError('configured campaign policy is missing')
    caps = dict(db.execute('SELECT currency, max_cents FROM campaign_currency_caps'))
    _validate_budget(policy['max_actions'], caps)
    count = db.execute('SELECT COUNT(*) FROM payments').fetchone()[0]
    spent = dict(db.execute('SELECT currency, SUM(amount_cents) FROM payments GROUP BY currency'))
    if count > policy['max_actions'] or any(currency not in caps or amount > caps[currency]
                                           for currency, amount in spent.items()):
        raise ValueError('committed payments exceed campaign policy')
    return {'max_actions': policy['max_actions'], 'currency_caps': caps,
            'charged_actions': count, 'remaining_actions': policy['max_actions'] - count,
            'charged_cents': {currency: spent.get(currency, 0) for currency in caps},
            'remaining_cents': {currency: cap - spent.get(currency, 0) for currency, cap in caps.items()},
            'authority': 'owned_sqlite_database_mock_only', 'deployment_authorized': False}


def budget_snapshot(path):
    """Policy and derived consumption share a read transaction; legacy is None."""
    with closing(connect(path)) as db, db:
        db.execute('BEGIN')
        return _budget_state(db)


def _check_budget(db, amount, currency):
    state = _budget_state(db)
    if state is None:
        return
    if currency not in state['currency_caps']:
        raise PermissionError('budget_currency_unregistered')
    if state['remaining_actions'] == 0:
        raise PermissionError('budget_action_limit')
    if amount > state['remaining_cents'][currency]:
        raise PermissionError('budget_currency_limit')


def snapshot(path):
    with closing(connect(path)) as db:
        return {name: [dict(row) for row in db.execute(f"SELECT * FROM {name} ORDER BY 1")]
                for name in ("approvals", "payments", "checkpoints")}


def revoke(path):
    with closing(connect(path)) as db, db:
        db.execute("UPDATE approvals SET granted=0 WHERE order_id=?", (ORDER,))


def issue_payment(path, key, order=ORDER, amount=AMOUNT, currency=CURRENCY, *, pause=None):
    if (not isinstance(key, str) or not key.strip() or type(amount) is not int
            or not 0 < amount <= MAX_INTEGER or not isinstance(order, str) or not order.strip()
            or not isinstance(currency, str) or not currency.strip()):
        raise ValueError("valid key and positive integer amount required")
    with closing(connect(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT * FROM payments WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            if (existing['order_id'], existing['amount_cents'], existing['currency']) != (order, amount, currency):
                raise ValueError("idempotency key conflicts with original action")
            return "already_committed"
        approval = db.execute("SELECT * FROM approvals WHERE order_id=?", (order,)).fetchone()
        if (approval is None or not approval['granted'] or approval['amount_cents'] != amount
                or approval['currency'] != currency):
            raise PermissionError("no current approval for the requested action")
        _check_budget(db, approval['amount_cents'], approval['currency'])
        db.execute("INSERT INTO payments VALUES (?, ?, ?, ?)", (key, order, amount, currency))
        _pause('inside_transaction', pause)
    return "committed"


def _pause(boundary, selected):
    if boundary == selected:
        print(json.dumps({"boundary": boundary, "pid": os.getpid()}), flush=True)
        sys.stdin.readline()  # Parent kills only this child after observing the marker.


def execute(path, *, pause=None, mode="reference"):
    if mode not in {"reference", "new-key-retry"}:
        raise ValueError("unsupported recovery mode")
    _pause("before_commit", pause)
    state = snapshot(path)
    checkpoint_complete = any(row['operation'] == OPERATION and row['status'] == 'complete'
                              for row in state['checkpoints'])
    # The mutant interprets a missing workflow checkpoint as a missing payment.
    key = OPERATION + ":retry" if mode == "new-key-retry" and not checkpoint_complete else OPERATION
    outcome = issue_payment(path, key, pause=pause)
    _pause("after_commit", pause)
    with closing(connect(path)) as db, db:
        db.execute("INSERT INTO checkpoints VALUES (?, 'complete') ON CONFLICT(operation) DO UPDATE SET status='complete'",
                   (OPERATION,))
    _pause("after_checkpoint", pause)
    return {"pid": os.getpid(), "payment_outcome": outcome, "checkpoint": "complete"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--pause", choices=("before_commit", "inside_transaction", "after_commit", "after_checkpoint"))
    parser.add_argument("--mode", choices=("reference", "new-key-retry"), default="reference")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("initialize a dedicated study database first")
    try:
        result = execute(args.database, pause=args.pause, mode=args.mode)
    except (ValueError, PermissionError, sqlite3.Error) as error:
        print(json.dumps({"pid": os.getpid(), "error_type": type(error).__name__, "error": str(error)}))
        return 2
    print(json.dumps(result), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
