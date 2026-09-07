"""Persist existing simulation decisions without duplicate state advancement."""

import multiprocessing
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab.durable_controller import DurableController
from cx_eval_lab.exposure_control import ExposureState, ExposureWindow, Observation


def initial():
    return ExposureState('candidate', 'baseline')


def window():
    return ExposureWindow('window-1', 'candidate', 'baseline', 0, 0, 10,
        (Observation('a', True, True, False, 10, 'artifact-a'),
         Observation('b', True, True, False, 10, 'artifact-b')))


def contender(path, identity, barrier, queue):
    controller = DurableController.open(path)
    barrier.wait(10)
    try:
        controller.apply(identity, initial(), window(), now=10)
        queue.put('accepted')
    except ValueError:
        queue.put('conflict')


def committed_worker(path, ready, release):
    DurableController.open(path).apply('decision', initial(), window(), now=10)
    ready.set()
    release.wait(30)


class DurableControllerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'controller.sqlite'
        self.controller = DurableController.initialize(self.path, initial())

    def test_reopen_replays_receipt_without_transition(self):
        receipt = self.controller.apply('decision', initial(), window(), now=10)
        reopened = DurableController.open(self.path)
        with patch('cx_eval_lab.durable_controller.transition', side_effect=AssertionError('no rerun')):
            self.assertEqual(reopened.apply('decision', initial(), window(), now=10), receipt)
        self.assertEqual(reopened.state().revision, 1)
        self.assertFalse(receipt['decision']['deployment_authorized'])

    def test_conflicting_receipt_or_predecessor_cannot_advance(self):
        self.controller.apply('decision', initial(), window(), now=10)
        with self.assertRaises(ValueError):
            self.controller.apply('decision', initial(), window(), now=11)
        with self.assertRaises(ValueError):
            self.controller.apply('other', initial(), window(), now=10)
        self.assertEqual(self.controller.state().revision, 1)

    def test_hold_state_is_compared_even_without_revision_change(self):
        missing = replace(window(), observations=tuple(replace(row, candidate_pass=None)
                                                      for row in window().observations))
        receipt = self.controller.apply('hold', initial(), missing, now=10)
        self.assertEqual(receipt['decision']['reason'], 'missing_mature_label')
        self.assertEqual(self.controller.state().revision, 0)
        with self.assertRaises(ValueError):
            self.controller.apply('stale', initial(), window(), now=10)
        self.controller.apply('mature', self.controller.state(), window(), now=10)
        self.assertEqual(self.controller.state().revision, 1)

    def test_transaction_failure_rolls_back_state_and_receipt(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER fail_update BEFORE UPDATE ON controller "
                       "BEGIN SELECT RAISE(ABORT, 'injected update failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.controller.apply('decision', initial(), window(), now=10)
        self.assertEqual(self.controller.state(), initial())
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0], 0)
            db.execute('DROP TRIGGER fail_update')
        self.controller.apply('decision', initial(), window(), now=10)

    def test_two_processes_cannot_accept_same_predecessor_twice(self):
        ctx = multiprocessing.get_context('spawn')
        barrier, queue = ctx.Barrier(2), ctx.Queue()
        children = [ctx.Process(target=contender, args=(self.path, str(i), barrier, queue)) for i in range(2)]
        for child in children:
            child.start()
        try:
            results = sorted(queue.get(timeout=15) for _ in children)
            self.assertEqual(results, ['accepted', 'conflict'])
        finally:
            for child in children:
                child.join(10)
                if child.is_alive():
                    child.kill()
                    child.join(10)
        self.assertEqual(self.controller.state().revision, 1)

    def test_kill_after_commit_recovers_same_decision(self):
        ctx = multiprocessing.get_context('spawn')
        ready, release = ctx.Event(), ctx.Event()
        child = ctx.Process(target=committed_worker, args=(self.path, ready, release))
        child.start()
        try:
            self.assertTrue(ready.wait(15))
            child.kill()
            child.join(10)
            self.assertFalse(child.is_alive())
        finally:
            if child.is_alive():
                child.kill()
                child.join(10)
        receipt = DurableController.open(self.path).apply('decision', initial(), window(), now=10)
        self.assertEqual(receipt['decision']['state']['revision'], 1)
        self.assertEqual(self.controller.state().revision, 1)

    def test_existing_missing_and_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            DurableController.initialize(self.path, initial())
        with self.assertRaises(ValueError):
            DurableController.open(self.path.with_name('missing'))
        for identity, now in (('', 10), ('decision', True), ('decision', -1)):
            with self.subTest(identity=identity, now=now), self.assertRaises(ValueError):
                self.controller.apply(identity, initial(), window(), now=now)
