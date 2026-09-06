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


def connect(path):
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA synchronous=FULL")
    return db


def initialize(path: Path):
    if path.exists():
        raise ValueError("recovery database already exists; use a new trial directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db, db:
        db.execute("CREATE TABLE approvals (order_id TEXT PRIMARY KEY, amount_cents INTEGER, currency TEXT, granted INTEGER)")
        db.execute("CREATE TABLE payments (idempotency_key TEXT PRIMARY KEY, order_id TEXT, amount_cents INTEGER, currency TEXT)")
        db.execute("CREATE TABLE checkpoints (operation TEXT PRIMARY KEY, status TEXT)")
        db.execute("INSERT INTO approvals VALUES (?, ?, ?, 1)", (ORDER, AMOUNT, CURRENCY))


def snapshot(path):
    with closing(connect(path)) as db:
        return {name: [dict(row) for row in db.execute(f"SELECT * FROM {name} ORDER BY 1")]
                for name in ("approvals", "payments", "checkpoints")}


def revoke(path):
    with closing(connect(path)) as db, db:
        db.execute("UPDATE approvals SET granted=0 WHERE order_id=?", (ORDER,))


def issue_payment(path, key, order=ORDER, amount=AMOUNT, currency=CURRENCY):
    if not isinstance(key, str) or not key or type(amount) is not int or amount <= 0:
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
        db.execute("INSERT INTO payments VALUES (?, ?, ?, ?)", (key, order, amount, currency))
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
    outcome = issue_payment(path, key)
    _pause("after_commit", pause)
    with closing(connect(path)) as db, db:
        db.execute("INSERT INTO checkpoints VALUES (?, 'complete') ON CONFLICT(operation) DO UPDATE SET status='complete'",
                   (OPERATION,))
    _pause("after_checkpoint", pause)
    return {"pid": os.getpid(), "payment_outcome": outcome, "checkpoint": "complete"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--pause", choices=("before_commit", "after_commit", "after_checkpoint"))
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
