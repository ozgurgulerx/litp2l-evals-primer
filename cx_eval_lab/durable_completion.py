"""Trusted-local completion journal; interrupted attempts cannot be resumed.

Effects and completion occupy separate transactions/databases. A started record
is missing persisted completion evidence, not proof of worker death. Identity
binds the local campaign inode, not cryptographic provenance or portable backup.
The caller-owned manifest digest must cover agent configuration/source and grader
identity; this module checks equality, not the honesty of that manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from cx_eval_lab.order_resolution import run_case


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _namespace(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty request namespace required')


def _binding(campaign):
    snapshot = campaign.snapshot()
    stat = campaign.path.stat()
    return _json({'path': str(campaign.path.resolve()), 'device': stat.st_dev,
                  'inode': stat.st_ino, 'campaign_id': snapshot['campaign_id'],
                  'max_actions': snapshot['max_actions'], 'currency_caps': snapshot['currency_caps']})


@dataclass(frozen=True)
class CompletionJournal:
    """Single-attempt reservation plus immutable full returned case evidence."""

    path: Path
    campaign: object
    binding: str

    @classmethod
    def initialize(cls, path, campaign):
        journal = cls(Path(path).absolute(), campaign, _binding(campaign))
        if journal.path.exists() or journal.path.is_symlink():
            raise ValueError('completion journal already exists')
        journal.path.parent.mkdir(parents=True, exist_ok=True)
        with journal.path.open('xb'):
            pass
        with closing(journal._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('PRAGMA user_version=1')
            db.execute('CREATE TABLE identity (binding TEXT NOT NULL)')
            db.execute('INSERT INTO identity VALUES (?)', (journal.binding,))
            db.execute("CREATE TABLE requests (namespace TEXT PRIMARY KEY, input TEXT NOT NULL, "
                       "status TEXT NOT NULL CHECK(status IN ('started','completed')), "
                       "artifact TEXT, artifact_hash TEXT, CHECK((status='started' AND artifact IS NULL "
                       "AND artifact_hash IS NULL) OR (status='completed' AND artifact IS NOT NULL "
                       "AND artifact_hash IS NOT NULL)))")
        return journal

    @classmethod
    def open(cls, path, campaign):
        journal = cls(Path(path).absolute(), campaign, _binding(campaign))
        with journal._transaction():
            pass
        return journal

    def _connect(self):
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError('existing regular completion journal required')
        db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=rw', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        return db

    @contextmanager
    def _transaction(self, *, write=False):
        if _binding(self.campaign) != self.binding:
            raise ValueError('campaign binding changed')
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('completion journal schema mismatch')
            rows = db.execute('SELECT binding FROM identity').fetchall()
            if len(rows) != 1 or rows[0][0] != self.binding:
                raise ValueError('completion journal campaign binding mismatch')
            yield db

    def _artifact(self, row):
        serialized = row['artifact']
        if not isinstance(serialized, str) or _hash(serialized) != row['artifact_hash']:
            raise ValueError('completion artifact hash mismatch')
        value = json.loads(serialized)
        if _json(value) != serialized:
            raise ValueError('completion artifact is not canonical JSON')
        identity = json.loads(row['input'])
        if (not isinstance(value, dict)
                or _json(value.get('case')) != _json(identity['case'])
                or _json(value.get('agent')) != _json(identity['agent'])
                or _json(value.get('reverse')) != _json(identity['reverse'])
                or _json(value.get('agent_input')) != _json(identity['case']['request'])
                or not isinstance(value.get('output'), dict)
                or not isinstance(value.get('orders'), list)
                or not isinstance(value.get('tool_events'), list)
                or not isinstance(value.get('durable_campaign'), dict)
                or value['durable_campaign'].get('campaign_id') != json.loads(self.binding)['campaign_id']
                or value['durable_campaign'].get('execution_namespace') != row['namespace']):
            raise ValueError('completion artifact request binding mismatch')
        return value

    def inspect(self, namespace):
        """Read persistence state only; no liveness or customer delivery claim."""
        _namespace(namespace)
        with self._transaction() as db:
            row = db.execute('SELECT * FROM requests WHERE namespace=?', (namespace,)).fetchone()
            if row is not None and row['status'] == 'completed':
                self._artifact(row)
            return {'status': 'not_registered' if row is None else row['status'],
                    'response_present': row is not None and row['status'] == 'completed',
                    'response_scope': 'persisted_completion_evidence_only', 'worker_liveness': 'unknown'}

    def inspect_many(self, bindings):
        """Bound read-only batch snapshot; missing records do not prove no work.

        Each binding contains namespace, case, agent name, reverse, and the
        caller-owned execution/grading manifest digest. No agent is invoked.
        """
        identities = []
        for binding in bindings:
            namespace = binding['namespace']
            _namespace(namespace)
            _namespace(binding['agent'])
            digest = binding['manifest_digest']
            if not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None:
                raise ValueError('explicit SHA-256 execution/grading manifest digest required')
            if type(binding['reverse']) is not bool:
                raise ValueError('reverse must be boolean')
            identities.append((namespace, _json({'case': asdict(binding['case']),
                'agent': binding['agent'], 'reverse': binding['reverse'], 'manifest_digest': digest})))
        if len({namespace for namespace, _ in identities}) != len(identities):
            raise ValueError('duplicate batch request namespace')
        with self._transaction() as db:
            results = []
            for namespace, identity in identities:
                row = db.execute('SELECT * FROM requests WHERE namespace=?', (namespace,)).fetchone()
                if row is not None and row['input'] != identity:
                    raise ValueError('request execution or grading identity conflict')
                results.append({'namespace': namespace, 'status': 'missing' if row is None else row['status'],
                    'artifact': self._artifact(row) if row is not None and row['status'] == 'completed' else None,
                    'worker_liveness': 'unknown'})
            return results

    def execute(self, case, agent, *, namespace, manifest_digest, reverse=False):
        """Return saved evidence, or reserve once and execute the existing runner."""
        _namespace(namespace)
        if not isinstance(manifest_digest, str) or re.fullmatch('[0-9a-f]{64}', manifest_digest) is None:
            raise ValueError('explicit SHA-256 execution/grading manifest digest required')
        if type(reverse) is not bool:
            raise ValueError('reverse must be boolean')
        _namespace(agent.name)
        identity = _json({'case': asdict(case), 'reverse': reverse, 'agent': agent.name,
                          'manifest_digest': manifest_digest})
        with self._transaction(write=True) as db:
            row = db.execute('SELECT * FROM requests WHERE namespace=?', (namespace,)).fetchone()
            if row is not None:
                if row['input'] != identity:
                    raise ValueError('request execution or grading identity conflict')
                if row['status'] != 'completed':
                    raise ValueError('incomplete attempt cannot be rerun or resumed')
                return self._artifact(row)
            db.execute("INSERT INTO requests VALUES (?, ?, 'started', NULL, NULL)", (namespace, identity))
        result = run_case(case, agent, reverse=reverse, execution_namespace=namespace,
                          durable_campaign=self.campaign)
        serialized = _json(result)
        validated = self._artifact({'artifact': serialized, 'artifact_hash': _hash(serialized),
                                    'input': identity, 'namespace': namespace})
        with self._transaction(write=True) as db:
            changed = db.execute("UPDATE requests SET status='completed', artifact=?, artifact_hash=? "
                                 "WHERE namespace=? AND input=? AND status='started'",
                                 (serialized, _hash(serialized), namespace, identity)).rowcount
            if changed != 1:
                raise ValueError('completion publication conflict')
        return validated
