"""Owned SQLite campaign for existing refund tools, not an external payment API.

The memory world is only a transaction-local transition engine. Persistent state,
events and refund effects become authoritative together at SQLite COMMIT.
"""

import json
import re
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from cx_eval_lab.models import RefundWorldSeed, ToolEvent, WorldSnapshot
from cx_eval_lab.world import RefundWorld, ToolTimeout

MAX_INTEGER = 2**63 - 1
CURRENCIES = frozenset({'USD', 'EUR', 'GBP'})
OPERATIONS = frozenset({'verify_identity', 'get_order', 'consult_refund_policy',
    'request_refund_approval', 'inspect_order_status', 'issue_refund',
    '_unsafe_issue_refund_for_test', '_invalidate_policy_for_test', '_commit_refund'})
TABLES = frozenset({'campaign', 'worlds', 'effects', 'events', 'request_starts'})
SCHEMA_VERSION = 2


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _identifier(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty trusted identifier required')


def _integer(value):
    if type(value) is not int or not 0 <= value <= MAX_INTEGER:
        raise ValueError('nonnegative int64 required')


def _seed_json(seed):
    if not isinstance(seed, RefundWorldSeed):
        raise ValueError('refund seed required')  # noqa: TRY004 - invalid configuration uses ValueError
    for identity in (seed.customer_id, seed.order_id):
        _identifier(identity)
    for value in (seed.amount_cents, seed.approval_threshold_cents):
        _integer(value)
    if (seed.currency not in CURRENCIES or type(seed.eligible) is not bool
            or type(seed.simulate_timeout_after_commit) is not bool
            or not isinstance(seed.competing_order_ids, tuple)):
        raise ValueError('invalid immutable refund seed')
    for identity in seed.competing_order_ids:
        _identifier(identity)
    return _json(asdict(seed))


def _expected_failure(engine, previous, error):
    state, events = previous
    added_events = engine._events[len(events):]
    if isinstance(error, ToolTimeout):
        keys = engine._snapshot.refund_idempotency_keys
        if (len(keys) != len(state.refund_idempotency_keys) + 1
                or keys[:-1] != state.refund_idempotency_keys
                or not engine._seed.simulate_timeout_after_commit or state.timeout_delivered):
            return False
        expected = ToolEvent(len(events) + 1, 'issue_refund', 'timed_out_after_commit', tuple(sorted({
            'idempotency_key': keys[-1], 'identity_verified': state.identity_verified,
            'policy_consulted': state.policy_consulted, 'approval_granted': state.approval_granted,
            'eligible': engine._seed.eligible}.items())))
        return (engine._snapshot == replace(state, refund_idempotency_keys=keys, timeout_delivered=True)
                and added_events == (expected,))
    expected_errors = {('get_order', 'not_found'): ValueError, ('get_order', 'access_denied'): PermissionError,
                       ('consult_refund_policy', 'not_found'): ValueError,
                       ('inspect_order_status', 'not_found'): ValueError, ('issue_refund', 'not_found'): ValueError}
    return (engine._snapshot == state and len(added_events) == 1
            and expected_errors.get((added_events[0].tool, added_events[0].status)) is type(error))


@dataclass(frozen=True, init=False)
class DurableCampaign:
    path: Path
    campaign_id: str
    _policy: str

    def __init__(self, path, *, campaign_id, max_actions, currency_caps):
        _identifier(campaign_id)
        _integer(max_actions)
        if not isinstance(currency_caps, dict):
            raise ValueError('currency caps must be a mapping')  # noqa: TRY004 - invalid configuration uses ValueError
        caps = dict(currency_caps)
        for currency, cap in caps.items():
            if currency not in CURRENCIES:
                raise ValueError('unregistered currency')
            _integer(cap)
        object.__setattr__(self, 'path', Path(path).absolute())
        object.__setattr__(self, 'campaign_id', campaign_id)
        object.__setattr__(self, '_policy', _json({'max_actions': max_actions, 'currency_caps': caps}))

    @classmethod
    def initialize(cls, path, **policy):
        campaign = cls(path, **policy)
        if campaign.path.exists() or campaign.path.is_symlink():
            raise ValueError('campaign database already exists')
        campaign.path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents concurrent initializers from replacing policy.
        with campaign.path.open('xb'):
            pass
        with closing(campaign._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('PRAGMA user_version=2')
            db.execute('CREATE TABLE campaign (campaign_id TEXT PRIMARY KEY, policy TEXT NOT NULL)')
            db.execute('CREATE TABLE worlds (namespace TEXT PRIMARY KEY, seed TEXT NOT NULL, state TEXT NOT NULL)')
            db.execute('CREATE TABLE effects (sequence INTEGER PRIMARY KEY, namespace TEXT NOT NULL REFERENCES worlds(namespace), '
                       'idempotency_key TEXT NOT NULL, order_id TEXT NOT NULL, amount_cents INTEGER NOT NULL, currency TEXT NOT NULL, '
                       'unsafe INTEGER NOT NULL, UNIQUE(namespace, idempotency_key))')
            db.execute('CREATE TABLE events (namespace TEXT NOT NULL REFERENCES worlds(namespace), sequence INTEGER NOT NULL, '
                       'tool TEXT NOT NULL, status TEXT NOT NULL, details TEXT NOT NULL, PRIMARY KEY(namespace, sequence))')
            db.execute("CREATE TABLE request_starts (namespace TEXT PRIMARY KEY, request_hash TEXT NOT NULL, "
                       "status TEXT NOT NULL CHECK(status='started'))")
            db.execute('INSERT INTO campaign VALUES (?, ?)', (campaign.campaign_id, campaign._policy))
        return campaign

    @classmethod
    def open(cls, path, **policy):
        campaign = cls(path, **policy)
        with campaign._transaction():
            pass
        return campaign

    def _connect(self):
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError('existing regular campaign database required')
        db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA foreign_keys=ON')
        return db

    @contextmanager
    def _transaction(self, *, write=False):
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not TABLES <= tables or db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
                raise ValueError('durable campaign schema mismatch')
            rows = db.execute('SELECT campaign_id, policy FROM campaign').fetchall()
            if len(rows) != 1 or tuple(rows[0]) != (self.campaign_id, self._policy):
                raise ValueError('durable campaign identity or policy mismatch')
            yield db

    def register(self, namespace, seed):
        _identifier(namespace)
        serialized = _seed_json(seed)
        with self._transaction(write=True) as db:
            row = db.execute('SELECT seed FROM worlds WHERE namespace=?', (namespace,)).fetchone()
            if row is not None:
                if row['seed'] != serialized:
                    raise ValueError('namespace conflicts with immutable world seed')
                return
            db.execute('INSERT INTO worlds VALUES (?, ?, ?)', (namespace, serialized, _json(asdict(WorldSnapshot()))))

    def _load(self, db, namespace, seed):
        row = db.execute('SELECT seed, state FROM worlds WHERE namespace=?', (namespace,)).fetchone()
        if row is None or row['seed'] != _seed_json(seed):
            raise ValueError('missing world or immutable seed conflict')
        keys = tuple(row[0] for row in db.execute(
            'SELECT idempotency_key FROM effects WHERE namespace=? ORDER BY sequence', (namespace,)))
        snapshot = WorldSnapshot(**{**json.loads(row['state']), 'refund_idempotency_keys': keys})
        events = tuple(ToolEvent(row['sequence'], row['tool'], row['status'],
                                tuple(sorted(json.loads(row['details']).items())))
                       for row in db.execute('SELECT * FROM events WHERE namespace=? ORDER BY sequence', (namespace,)))
        return snapshot, events

    def read_world(self, namespace, seed):
        with self._transaction() as db:
            return self._load(db, namespace, seed)

    def read_worlds(self, bindings):
        """Project all requested worlds/events from one shared read transaction."""
        with self._transaction() as db:
            return {namespace: self._load(db, namespace, seed) for namespace, seed in bindings.items()}

    def admit_request(self, namespace, request_hash, bindings):
        """Fence one high-level execution, including zero-tool attempts; no resume.

        The marker is durable even if the process dies before its first tool call.
        This is admission only, not a recovered trajectory or controller checkpoint.
        """
        _identifier(namespace)
        if not isinstance(request_hash, str) or re.fullmatch(r'sha256:[0-9a-f]{64}', request_hash) is None:
            raise ValueError('canonical operational request digest required')
        with self._transaction(write=True) as db:
            previous = db.execute('SELECT request_hash FROM request_starts WHERE namespace=?', (namespace,)).fetchone()
            if previous is not None:
                if previous['request_hash'] != request_hash:
                    raise ValueError('request namespace conflicts with immutable operational input')
                raise ValueError('prior execution evidence or request admission prevents reexecution')
            states = [self._load(db, world_namespace, seed) for world_namespace, seed in bindings.items()]
            if any(state != WorldSnapshot() or events for state, events in states):
                raise ValueError('prior execution evidence requires an explicit durable attempt recovery contract')
            db.execute("INSERT INTO request_starts VALUES (?, ?, 'started')", (namespace, request_hash))

    def _balance(self, db):
        policy = json.loads(self._policy)
        caps = policy['currency_caps']
        effects = [{**dict(row), 'unsafe': bool(row['unsafe'])}
                   for row in db.execute('SELECT * FROM effects ORDER BY sequence')]
        spent = {currency: sum(row['amount_cents'] for row in effects if row['currency'] == currency)
                 for currency in caps}
        return {'campaign_id': self.campaign_id, **policy,
                'charged_actions': len(effects), 'remaining_actions': policy['max_actions'] - len(effects),
                'charged_cents': spent, 'remaining_cents': {currency: cap - spent[currency] for currency, cap in caps.items()},
                'effects': effects, 'authority': 'owned_sqlite_mock_only', 'deployment_authorized': False}

    def snapshot(self):
        with self._transaction() as db:
            return self._balance(db)

    def _guard(self, db, seed):
        balance = self._balance(db)
        if seed.currency not in balance['currency_caps']:
            return 'budget_currency_unregistered'
        if balance['remaining_actions'] <= 0:
            return 'budget_action_limit'
        if seed.amount_cents > balance['remaining_cents'][seed.currency]:
            return 'budget_currency_limit'
        return None

    def _save(self, db, namespace, engine, previous, method):
        state = asdict(engine._snapshot)
        # Refund keys are always projected from effects, not trusted from this copy.
        state.pop('refund_idempotency_keys')
        db.execute('UPDATE worlds SET state=? WHERE namespace=?', (_json(state), namespace))
        for key in engine._snapshot.refund_idempotency_keys[len(previous[0].refund_idempotency_keys):]:
            db.execute('INSERT INTO effects (namespace, idempotency_key, order_id, amount_cents, currency, unsafe) '
                       'VALUES (?, ?, ?, ?, ?, ?)',
                       (namespace, key, engine._seed.order_id, engine._seed.amount_cents, engine._seed.currency,
                        int(method in {'_unsafe_issue_refund_for_test', '_commit_refund'})))
        for event in engine._events[len(previous[1]):]:
            db.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?)',
                       (namespace, event.sequence, event.tool, event.status, _json(dict(event.details))))

    def invoke(self, world, method, *args, **kwargs):
        if method == 'reset':
            raise RuntimeError('durable worlds cannot reset authority or consumed identity')
        if method not in OPERATIONS:
            raise ValueError('unregistered durable world operation')
        failure = None
        result = None
        with self._transaction(write=True) as db:
            previous = self._load(db, world.execution_namespace, world._seed)
            engine = RefundWorld(world._seed)
            engine._snapshot, engine._events = previous
            engine._durable_effect_guard = lambda order, key: self._guard(db, world._seed)
            try:
                result = getattr(engine, method)(*args, **kwargs)
            except (ValueError, PermissionError, ToolTimeout) as error:
                # Exception class alone is not evidence of an expected boundary.
                # Unknown partial mutation must roll back even for these classes.
                if not _expected_failure(engine, previous, error):
                    raise
                failure = error
            self._save(db, world.execution_namespace, engine, previous, method)
        if failure is not None:
            raise failure
        return result
