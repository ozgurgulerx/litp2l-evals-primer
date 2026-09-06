"""Local synthetic incident -> reviewed regression, never acceptance promotion."""
from dataclasses import asdict, dataclass, replace
import argparse
import json
from pathlib import Path
import re

from cx_eval_lab.agents import MutantSupportAgent, ReferenceSupportAgent
from cx_eval_lab.evaluators import evaluate_case
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import RefundCase
from cx_eval_lab.world import RefundTools, RefundWorld

POLICY = 'refund-policy-v1'
TRANSFORM = 'remove-synthetic-padding-and-distractors-v1'


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('invalid synthetic identifier')


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch('sha256:[a-f0-9]{64}', value):
        raise ValueError('invalid evidence hash')


def _object(value):
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError('evidence must be a finite JSON object')
    _json(parsed)
    return parsed


def content_hash(case):
    """Exact operational content identity, invariant to dataset/case label renaming."""
    return canonical_hash({k: v for k, v in case.to_dict().items()
                           if k not in ('case_id', 'dataset_version', 'slices')})


def execute(case, control='mutant'):
    if control not in ('reference', 'mutant'):
        raise ValueError('unknown deterministic control')
    world = RefundWorld.from_case(case)
    initial = asdict(world.snapshot)
    agent = ReferenceSupportAgent() if control == 'reference' else MutantSupportAgent('blind-retry')
    output = agent.run(case.agent_input, RefundTools(world, fault_mode='duplicate-effect'))
    result = evaluate_case(case, output, world.events, world.snapshot, latency_ms=0, cost_usd=None)
    # Grader requires latency; zero is a placeholder excluded from retained metrics.
    return json.loads(_json({'control': control, 'case': case.to_dict(), 'initial_state': initial,
            'events': [event.to_dict() for event in world.events], 'output': asdict(output),
            'final_state': {**asdict(world.snapshot), 'refund_transaction_count': world.snapshot.refund_transaction_count},
            'fault_mode': 'duplicate-effect', 'passed': result.passed,
            'failed_checks': [check.name for check in result.checks if not check.passed],
            'duplicate_refund_count': result.duplicate_refund_count,
            'measurement': 'no cost or latency evidence claimed'}))


@dataclass(frozen=True)
class Incident:
    incident_id: str
    group_id: str
    case: RefundCase
    execution_json: str
    domain_policy: str = POLICY

    def __post_init__(self):
        _identifier(self.incident_id)
        _identifier(self.group_id)
        if not isinstance(self.case, RefundCase) or self.domain_policy != POLICY:
            raise ValueError('unsupported incident case/policy')
        object.__setattr__(self, 'execution_json', _json(_object(self.execution_json)))

    def to_dict(self):
        return {**asdict(self), 'case': self.case.to_dict(), 'execution': _object(self.execution_json)}

    @property
    def digest(self):
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class Proposal:
    incident_hash: str
    case: RefundCase
    proposer_id: str = 'synthetic-proposer'
    domain_policy: str = POLICY
    transformation: str = TRANSFORM
    target_version: str = 'regression-v1'
    target_role: str = 'regression'

    def __post_init__(self):
        _hash(self.incident_hash)
        _identifier(self.proposer_id)
        _identifier(self.target_version)
        if (not isinstance(self.case, RefundCase) or self.domain_policy != POLICY
                or self.transformation != TRANSFORM or self.target_role != 'regression'):
            raise ValueError('unsupported proposal contract')

    @property
    def digest(self):
        return canonical_hash(asdict(self))


@dataclass(frozen=True)
class Review:
    incident_hash: str
    proposer_hash: str  # Exact full proposal hash, including target and transformation.
    reviewer_id: str
    domain_policy: str
    decision: str
    privacy_review: str
    privacy_scope: str = 'source-and-proposed-case-and-all-retained-execution-fields'

    def __post_init__(self):
        _hash(self.incident_hash)
        _hash(self.proposer_hash)
        _identifier(self.reviewer_id)
        if (self.decision not in ('approved', 'rejected') or self.privacy_review not in ('approved', 'pending')
                or not isinstance(self.domain_policy, str) or self.privacy_scope !=
                'source-and-proposed-case-and-all-retained-execution-fields'):
            raise ValueError('invalid review contract')


@dataclass(frozen=True)
class Inventory:
    role: str
    groups: tuple[str, ...] = ()
    source_hashes: tuple[str, ...] = ()
    content_hashes: tuple[str, ...] = ()

    def __post_init__(self):
        if self.role not in ('sealed-acceptance', 'judge-calibration'):
            raise ValueError('only protected-role inventories are supported')
        for field in ('groups', 'source_hashes', 'content_hashes'):
            values = getattr(self, field)
            if not isinstance(values, tuple):
                raise ValueError('inventory entries must be immutable tuples')
            for value in values:
                (_identifier if field == 'groups' else _hash)(value)


@dataclass(frozen=True)
class RegressionRelease:
    version: str
    entries: tuple[str, ...] = ()
    parent_hash: str | None = None
    role: str = 'regression'

    def __post_init__(self):
        _identifier(self.version)
        if self.role != 'regression' or not isinstance(self.entries, tuple):
            raise ValueError('immutable regression-only releases required')
        if self.parent_hash is not None:
            _hash(self.parent_hash)
        rows = [_object(entry) for entry in self.entries]
        keys = {'case', 'content_hash', 'source_incident_hash', 'group_id', 'proposal_hash',
                'review_hash', 'transformation', 'diff'}
        for row in rows:
            if set(row) != keys or not isinstance(row['case'], dict):
                raise ValueError('invalid parent entry schema')
            case = RefundCase.from_dict(row['case'])
            if row['content_hash'] != content_hash(case) or row['transformation'] != TRANSFORM:
                raise ValueError('parent content identity or transformation mismatch')
            _identifier(row['group_id'])
            for field in ('source_incident_hash', 'proposal_hash', 'review_hash'):
                _hash(row[field])
            if not isinstance(row['diff'], dict):
                raise ValueError('invalid retained transformation diff')
        if (len({row['content_hash'] for row in rows}) != len(rows)
                or len({row['case']['case_id'] for row in rows}) != len(rows)):
            raise ValueError('duplicate parent entries')

    def to_dict(self):
        return {**asdict(self), 'entries': [_object(entry) for entry in self.entries]}

    @property
    def digest(self):
        return canonical_hash(self.to_dict())

    def materialize(self):
        """Load retained cases into the current release version for the CX runner."""
        return tuple(replace(RefundCase.from_dict(_object(entry)['case']), dataset_version=self.version)
                     for entry in self.entries)


def capture_incident():
    case = RefundCase('synthetic-source-01', 'synthetic-customer', 'synthetic-order',
        'Synthetic padding: hello. Please refund this order. Synthetic padding: thank you.',
        1500, True, 5000, 'refunded', ('synthetic-incident',),
        competing_order_ids=('synthetic-distractor-1', 'synthetic-distractor-2'),
        simulate_timeout_after_commit=True)
    return Incident('synthetic-incident-01', 'synthetic-session-01', case, _json(execute(case)))


def _mechanism(case, execution):
    return (case.simulate_timeout_after_commit and execution['duplicate_refund_count'] == 1
            and execution['final_state']['refund_transaction_count'] == 2 and not execution['passed']
            and any(event['tool'] == 'issue_refund' and event['status'] == 'timed_out_after_commit'
                    for event in execution['events']))


def _validate_incident(incident):
    execution = execute(incident.case)
    if execution != _object(incident.execution_json) or not _mechanism(incident.case, execution):
        raise ValueError('source incident does not reproduce the registered duplicate-after-timeout mechanism')


def propose_regression(incident, *, target_version='regression-v1'):
    _validate_incident(incident)
    case = replace(incident.case, case_id=f'regression-{incident.incident_id}', utterance='Please refund this order.',
                   competing_order_ids=(), dataset_version=target_version)
    proposal = Proposal(incident.digest, case, target_version=target_version)
    if not _mechanism(case, execute(case)) or not execute(case, 'reference')['passed']:
        raise ValueError('minimized control does not preserve failure and reference success')
    return proposal


def promote(parent, incident, proposal, review, inventories=()):
    _validate_incident(incident)
    expected = propose_regression(incident, target_version=proposal.target_version)
    if (proposal != expected or review is None or review.decision != 'approved'
            or review.privacy_review != 'approved' or review.incident_hash != incident.digest
            or review.proposer_hash != proposal.digest or review.domain_policy != incident.domain_policy
            or review.reviewer_id == proposal.proposer_id or parent.version == proposal.target_version):
        raise ValueError('promotion requires exact independent synthetic review and a fresh target version')
    if not isinstance(inventories, tuple) or not all(isinstance(row, Inventory) for row in inventories):
        raise ValueError('operator inventory must be a tuple of validated protected inventories')
    identities = {content_hash(incident.case), content_hash(proposal.case)}
    for inventory in inventories:
        if (incident.group_id in inventory.groups or incident.digest in inventory.source_hashes
                or identities.intersection(inventory.content_hashes)):
            raise ValueError('known protected-role lineage or content conflict')
    existing = [_object(entry) for entry in parent.entries]
    if any(entry['content_hash'] == content_hash(proposal.case)
           or entry['case']['case_id'] == proposal.case.case_id for entry in existing):
        raise ValueError('duplicate content or conflicting case identity')
    entry = {'case': proposal.case.to_dict(), 'content_hash': content_hash(proposal.case),
             'source_incident_hash': incident.digest, 'group_id': incident.group_id,
             'proposal_hash': proposal.digest, 'review_hash': canonical_hash(asdict(review)),
             'transformation': proposal.transformation,
             'diff': {key: {'before': incident.case.to_dict()[key], 'after': value}
                      for key, value in proposal.case.to_dict().items() if incident.case.to_dict()[key] != value}}
    return RegressionRelease(proposal.target_version, (*parent.entries, _json(entry)), parent.digest)


def run_study():
    incident = capture_incident()
    proposal = propose_regression(incident)
    review = Review(incident.digest, proposal.digest, 'synthetic-reviewer', POLICY, 'approved', 'approved')
    parent = RegressionRelease('regression-v0')
    child = promote(parent, incident, proposal, review)
    controls = {}
    for name, decision, inventories in (
        ('unreviewed', None, ()), ('rejected', replace(review, decision='rejected'), ()),
        ('privacy-pending', replace(review, privacy_review='pending'), ()),
        ('stale-review', replace(review, proposer_hash='sha256:' + '0' * 64), ()),
        ('same-reviewer', replace(review, reviewer_id=proposal.proposer_id), ()),
        ('sealed-lineage', review, (Inventory('sealed-acceptance', (incident.group_id,)),)),
        ('calibration-content', review, (Inventory('judge-calibration', content_hashes=(content_hash(proposal.case),)),))):
        try:
            promote(parent, incident, proposal, decision, inventories)
        except ValueError as error:
            controls[name] = {'rejected': True, 'reason': str(error)}
        else:
            controls[name] = {'rejected': False}
    released_case = child.materialize()[0]
    reruns = {control: execute(released_case, control) for control in ('reference', 'mutant')}
    report = {'schema': 'incident-regression-study-v1', 'incident': incident.to_dict(),
        'proposal': asdict(proposal), 'review': asdict(review), 'parent': parent.to_dict(),
        'release': child.to_dict(), 'release_hash': child.digest, 'controls': controls, 'reruns': reruns,
        'conformance_passed': all(row['rejected'] for row in controls.values())
            and reruns['reference']['passed'] and _mechanism(proposal.case, reruns['mutant']),
        'deployment_authorized': False,
        'limitations': 'Local synthetic fixtures and scripted controls, not real incidents or authenticated human '
            'reviewers. Privacy approval covers retained source/candidate/execution fields but is a synthetic '
            'decision, not automatic PII removal. Exact operational-content duplicate checks are not semantic '
            'deduplication. Only supplied known protected inventories are checked; empty inventories do not '
            'prove absence of contamination. Regression-only release; no sealed acceptance promotion, measured '
            'latency/cost, source attestation, model capability or deployment qualification. Fixed synthetic '
            'transformation, not a general minimizer. The duplicate-effect tool fault deliberately defeats '
            'idempotency for both controls; this is not a failure of the normal backend boundary. Parent '
            'records are structurally checked but no external parent-release authority is authenticated.'}
    return {**report, 'report_hash': canonical_hash(report)}


def replay_study(report):
    owned = json.loads(_json(report))
    if owned != json.loads(_json(run_study())):
        raise ValueError('retained incident study differs from deterministic re-execution and reviewed release')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return 0 if report['conformance_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
