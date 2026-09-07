"""Real SQLite campaign enforcement across independent processes and crashes."""

import json
import multiprocessing
import select
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from cx_eval_lab import recovery_worker as worker


def compete(path, key, barrier, queue):
    barrier.wait(timeout=10)
    try:
        result = worker.issue_payment(path, key)
    except PermissionError as error:
        result = str(error)
    queue.put((key, result))


class RecoveryBudgetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'ledger.sqlite'

    def initialize(self, count=1, caps=None):
        worker.initialize(self.path, max_actions=count, currency_caps={'USD': 4000} if caps is None else caps)

    def approve(self, order, amount, currency):
        with closing(worker.connect(self.path)) as db, db:
            db.execute('INSERT OR REPLACE INTO approvals VALUES (?, ?, ?, 1)', (order, amount, currency))

    def test_policy_count_and_currency_boundaries_are_persisted(self):
        self.initialize(3, {'USD': 4000, 'EUR': 4500})
        self.approve('eur', 4500, 'EUR')
        self.approve('gbp', 1, 'GBP')
        self.assertEqual(worker.issue_payment(self.path, 'usd'), 'committed')
        with self.assertRaisesRegex(PermissionError, 'currency_limit'):
            worker.issue_payment(self.path, 'usd-new')
        self.assertEqual(worker.issue_payment(self.path, 'eur', 'eur', 4500, 'EUR'), 'committed')
        with self.assertRaisesRegex(PermissionError, 'currency_unregistered'):
            worker.issue_payment(self.path, 'gbp', 'gbp', 1, 'GBP')
        state = worker.budget_snapshot(self.path)
        self.assertEqual(state['charged_actions'], 2)
        self.assertEqual(state['remaining_cents'], {'EUR': 0, 'USD': 0})
        self.assertFalse(state['deployment_authorized'])

    def test_replay_survives_exhaustion_and_revocation_but_new_action_needs_approval(self):
        self.initialize(1, {'USD': 8000})
        worker.issue_payment(self.path, worker.OPERATION)
        with self.assertRaisesRegex(PermissionError, 'action_limit'):
            worker.issue_payment(self.path, 'new')
        worker.revoke(self.path)
        self.assertEqual(worker.issue_payment(self.path, worker.OPERATION), 'already_committed')
        with self.assertRaisesRegex(PermissionError, 'approval'):
            worker.issue_payment(self.path, 'new')
        for changes in ({'order': 'other'}, {'amount': 4001}, {'currency': 'EUR'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                worker.issue_payment(self.path, worker.OPERATION, **changes)
        self.assertEqual(worker.budget_snapshot(self.path)['charged_actions'], 1)

    def test_invalid_policy_rejected_before_creating_database(self):
        policies = [(True, {'USD': 1}), (-1, {}), (2**63, {}), (1, {'USD': True}),
                    (1, {'USD': -1}), (1, {'USD': 2**63}), (1, {'XXX': 1}),
                    (1, {'usd': 1}), (1, []), (None, {}), (1, None)]
        for count, caps in policies:
            with self.subTest(count=count, caps=caps), self.assertRaises(ValueError):
                worker.initialize(self.path, max_actions=count, currency_caps=caps)
            self.assertFalse(self.path.exists())

    def test_zero_caps_and_integer_max_without_overflow(self):
        self.initialize(0)
        with self.assertRaises(PermissionError):
            worker.issue_payment(self.path, 'zero')
        other = self.path.with_name('max.sqlite')
        maximum = 2**63 - 1
        worker.initialize(other, max_actions=maximum, currency_caps={'USD': maximum})
        with closing(worker.connect(other)) as db, db:
            db.execute('UPDATE approvals SET amount_cents=?', (maximum,))
        worker.issue_payment(other, 'maximum', amount=maximum)
        self.assertEqual(worker.budget_snapshot(other)['remaining_cents'], {'USD': 0})
        with self.assertRaisesRegex(PermissionError, 'currency_limit'):
            worker.issue_payment(other, 'next', amount=maximum)
        for amount in (True, 0, -1, 2**63):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                worker.issue_payment(other, 'invalid', amount=amount)

    def test_policy_cannot_be_reset_and_legacy_snapshot_is_unchanged(self):
        self.initialize()
        for count in (1, 10):
            with self.assertRaises(ValueError):
                worker.initialize(self.path, max_actions=count, currency_caps={'USD': 40000})
        worker.issue_payment(self.path, 'effect')
        with self.assertRaises(ValueError):
            worker.initialize(self.path)
        self.assertEqual(set(worker.snapshot(self.path)), {'approvals', 'payments', 'checkpoints'})
        other = self.path.with_name('legacy.sqlite')
        worker.initialize(other)
        self.assertIsNone(worker.budget_snapshot(other))
        worker.issue_payment(other, 'one')
        worker.issue_payment(other, 'two')
        self.assertEqual(len(worker.snapshot(other)['payments']), 2)

    def test_separate_processes_compete_for_last_unit(self):
        self.initialize()
        context = multiprocessing.get_context('spawn')
        barrier, queue = context.Barrier(3), context.Queue()
        children = [context.Process(target=compete, args=(str(self.path), key, barrier, queue))
                    for key in ('first', 'second')]
        try:
            for child in children:
                child.start()
            barrier.wait(timeout=10)
            results = [queue.get(timeout=10)[1] for _ in children]
            for child in children:
                child.join(timeout=10)
                self.assertEqual(child.exitcode, 0)
            self.assertCountEqual(results, ['committed', 'budget_action_limit'])
            self.assertEqual(len(worker.snapshot(self.path)['payments']), 1)
        finally:
            for child in children:
                if child.is_alive():
                    child.kill()
                child.join(timeout=5)
            queue.close()
            queue.join_thread()

    def interrupt(self, boundary):
        command = [sys.executable, '-m', 'cx_eval_lab.recovery_worker', '--database', str(self.path), '--pause', boundary]
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as child:
            try:
                ready, _, _ = select.select([child.stdout], [], [], 10)
                self.assertTrue(ready, 'child must reach registered crash boundary')
                marker = json.loads(child.stdout.readline())
                self.assertEqual(marker['boundary'], boundary)
                child.kill()
                child.wait(timeout=5)
                self.assertLess(child.returncode, 0)
            finally:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=5)

    def test_kill_after_commit_resume_does_not_charge_again(self):
        self.initialize()
        self.interrupt('after_commit')
        self.assertEqual(worker.budget_snapshot(self.path)['charged_actions'], 1)
        self.assertEqual(worker.snapshot(self.path)['checkpoints'], [])
        worker.revoke(self.path)
        self.assertEqual(worker.execute(self.path)['payment_outcome'], 'already_committed')
        self.assertEqual(worker.budget_snapshot(self.path)['charged_actions'], 1)

    def test_kill_inside_transaction_rolls_back_payment_and_consumption(self):
        self.initialize()
        self.interrupt('inside_transaction')
        self.assertEqual(worker.budget_snapshot(self.path)['charged_actions'], 0)
        self.assertEqual(worker.snapshot(self.path)['payments'], [])
        self.assertEqual(worker.execute(self.path)['payment_outcome'], 'committed')
        self.assertEqual(worker.budget_snapshot(self.path)['charged_actions'], 1)

    def test_sql_error_cannot_fall_back_to_uncapped_payment(self):
        self.initialize()
        with closing(worker.connect(self.path)) as db, db:
            db.execute('DROP TABLE campaign_currency_caps')
        with self.assertRaises(sqlite3.Error):
            worker.issue_payment(self.path, 'failure')
        self.assertEqual(worker.snapshot(self.path)['payments'], [])
