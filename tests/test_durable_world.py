"""Existing refund tools use one durable authority/effect transaction."""

import multiprocessing
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab.action_budget import ActionBudget
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.models import RefundWorldSeed
from cx_eval_lab.world import RefundTools, RefundWorld, ToolTimeout

SEED = RefundWorldSeed('customer', 'order', 4000, 'USD', True, 10000, False)
POLICY = {'campaign_id': 'campaign', 'max_actions': 1, 'currency_caps': {'USD': 4000}}


def authorize(world):
    tools = RefundTools(world)
    tools.verify_identity('customer', 'order')
    tools.consult_refund_policy('order')
    return tools


def refund(tools, key='key'):
    return tools.issue_refund('order', 4000, 'USD', None, key)


def compete(path, namespace, barrier, queue):
    campaign = DurableCampaign.open(path, **POLICY)
    world = RefundWorld(SEED, durable_campaign=campaign, execution_namespace=namespace)
    tools = authorize(world)
    barrier.wait(timeout=10)
    queue.put(refund(tools)['status'])


class DurableWorldTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'world.sqlite'
        self.campaign = DurableCampaign.initialize(self.path, **POLICY)

    def world(self, namespace='world', seed=SEED, campaign=None):
        return RefundWorld(seed, durable_campaign=self.campaign if campaign is None else campaign,
                           execution_namespace=namespace)

    def test_existing_tools_and_persisted_events_after_reopen(self):
        world = self.world()
        tools = authorize(world)
        self.assertEqual(refund(tools)['status'], 'committed')
        before = world.durable_state()
        reopened = self.world(campaign=DurableCampaign.open(self.path, **POLICY))
        self.assertEqual(reopened.durable_state(), before)
        self.assertEqual(refund(RefundTools(reopened))['status'], 'already_committed')
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
        self.assertEqual(reopened.events[-1].status, 'idempotent_replay')

    def test_auth_first_replay_rechecks_revocation_and_status_reconciles(self):
        old = self.world()
        refund(authorize(old))
        self.world().verify_identity('revoked', 'order')
        self.assertFalse(old.snapshot.identity_verified)
        self.assertEqual(refund(RefundTools(old))['reason'], 'identity_not_verified')
        self.assertTrue(old.inspect_order_status('order')['refunded'])
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)

    def test_new_key_exhaustion_and_changed_parameters(self):
        world = self.world()
        tools = authorize(world)
        refund(tools)
        self.assertEqual(refund(tools, 'new')['reason'], 'budget_action_limit')
        self.assertEqual(tools.issue_refund('order', 1, 'USD', None, 'key')['reason'], 'amount_mismatch')
        self.assertEqual(tools.issue_refund('order', 4000, 'EUR', None, 'key')['reason'], 'currency_mismatch')
        self.assertEqual(world.snapshot.refund_transaction_count, 1)

    def test_timeout_is_raised_only_after_effect_and_event_are_durable(self):
        seed = replace(SEED, simulate_timeout_after_commit=True)
        world = self.world(seed=seed)
        with self.assertRaises(ToolTimeout):
            refund(authorize(world))
        reopened = self.world(seed=seed)
        self.assertTrue(reopened.snapshot.timeout_delivered)
        self.assertEqual(reopened.events[-1].status, 'timed_out_after_commit')
        self.assertEqual(refund(RefundTools(reopened))['status'], 'already_committed')
        self.assertEqual(self.campaign.snapshot()['charged_cents'], {'USD': 4000})

    def test_seed_namespace_identity_and_reset_are_fail_closed(self):
        self.world()
        for field in ('customer_id', 'currency', 'amount_cents'):
            value = {'customer_id': 'other', 'currency': 'EUR', 'amount_cents': 3999}[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.world(seed=replace(SEED, **{field: value}))
        with self.assertRaises(RuntimeError):
            self.world().reset()
        with self.assertRaises(ValueError):
            RefundWorld(SEED, durable_campaign=self.campaign)
        with self.assertRaises(ValueError):
            RefundWorld(SEED, durable_campaign=self.campaign, execution_namespace='x',
                        action_budget=ActionBudget(1, {'USD': 4000}))

    def test_campaign_open_validates_policy_and_missing_schema(self):
        for changes in ({'campaign_id': 'other'}, {'max_actions': 2}, {'currency_caps': {'USD': 1}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                DurableCampaign.open(self.path, **{**POLICY, **changes})
        with self.assertRaises(ValueError):
            DurableCampaign.initialize(self.path, **POLICY)
        with self.assertRaises(ValueError):
            DurableCampaign.open(self.path.with_name('missing.sqlite'), **POLICY)
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TABLE effects')
        with self.assertRaises((ValueError, sqlite3.Error)):
            self.world()

    def test_invalid_policy_and_seed_never_reach_effect(self):
        for count, caps in [(True, {}), (-1, {}), (2**63, {}), (1, {'USD': True}),
                            (1, {'USD': -1}), (1, {'USD': 2**63}), (1, {'XXX': 1})]:
            with self.subTest(count=count, caps=caps), self.assertRaises(ValueError):
                DurableCampaign.initialize(self.path.with_name('invalid'), campaign_id='c', max_actions=count,
                                           currency_caps=caps)
        for amount in (True, -1, 2**63):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.world(seed=replace(SEED, amount_cents=amount))

    def test_unsafe_seams_still_commit_bad_behavior_but_cannot_escape_cap(self):
        world = self.world()
        tools = RefundTools(world, 'authorization-bypass')
        self.assertEqual(refund(tools)['status'], 'committed')
        self.assertFalse(world.snapshot.identity_verified)
        self.assertFalse(dict(world.events[-1].details)['identity_verified'])
        other = self.world('other')
        self.assertEqual(refund(RefundTools(other, 'duplicate-effect'))['status'], 'blocked')
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
        self.assertTrue(self.campaign.snapshot()['effects'][0]['unsafe'])

    def test_zero_count_currency_cap_and_unknown_currency_block_effects(self):
        for index, (count, caps, reason) in enumerate([(0, {'USD': 4000}, 'budget_action_limit'),
                (1, {'USD': 0}, 'budget_currency_limit'), (1, {'EUR': 4000}, 'budget_currency_unregistered')]):
            campaign = DurableCampaign.initialize(self.path.with_name(f'zero-{index}'),
                campaign_id='zero', max_actions=count, currency_caps=caps)
            world = self.world(campaign=campaign)
            self.assertEqual(refund(authorize(world))['reason'], reason)
            self.assertEqual(world.snapshot.refund_transaction_count, 0)

    def test_approval_and_error_traces_are_persisted(self):
        world = self.world()
        with self.assertRaises(PermissionError):
            world.get_order('order')
        self.assertEqual(self.world().events[-1].status, 'access_denied')
        authorize(world)
        world.request_refund_approval('order', 4000, 'USD')
        self.assertTrue(self.world().snapshot.approval_granted)
        world._invalidate_policy_for_test()
        self.assertEqual(refund(RefundTools(world))['reason'], 'policy_not_consulted')

    def test_persistence_failure_rolls_back_authority_and_effects(self):
        world = self.world()
        tools = authorize(world)
        before = world.durable_state()
        with patch.object(DurableCampaign, '_save', side_effect=RuntimeError('storage failure')), self.assertRaises(RuntimeError):
            refund(tools)
        self.assertEqual(world.durable_state(), before)
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 0)

    def test_internal_expected_error_types_do_not_commit_partial_effect(self):
        for error in (ValueError, PermissionError, ToolTimeout):
            with self.subTest(error=error.__name__):
                campaign = DurableCampaign.initialize(self.path.with_name(error.__name__), **POLICY)
                world = self.world(campaign=campaign)
                tools = authorize(world)
                before = world.durable_state()
                with patch.object(RefundWorld, '_record', side_effect=error('internal recorder failure')), self.assertRaises(error):
                    refund(tools)
                self.assertEqual(world.durable_state(), before)
                self.assertEqual(campaign.snapshot()['charged_actions'], 0)

    def test_error_after_sql_writes_rolls_back_state_effect_and_event(self):
        world = self.world()
        tools = authorize(world)
        before = world.durable_state()
        original = DurableCampaign._save
        def fail_after_write(campaign, *args):
            original(campaign, *args)
            raise RuntimeError('failed before commit')
        with patch.object(DurableCampaign, '_save', fail_after_write), self.assertRaises(RuntimeError):
            refund(tools)
        self.assertEqual(world.durable_state(), before)
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 0)

    def test_two_processes_compete_for_final_campaign_unit(self):
        context = multiprocessing.get_context('spawn')
        barrier, queue = context.Barrier(3), context.Queue()
        children = [context.Process(target=compete, args=(str(self.path), namespace, barrier, queue))
                    for namespace in ('first', 'second')]
        try:
            for child in children:
                child.start()
            barrier.wait(timeout=10)
            results = [queue.get(timeout=10) for _ in children]
            for child in children:
                child.join(timeout=10)
                self.assertEqual(child.exitcode, 0)
            self.assertCountEqual(results, ['committed', 'blocked'])
            self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
        finally:
            for child in children:
                if child.is_alive():
                    child.kill()
                child.join(timeout=5)
            queue.close()
            queue.join_thread()
