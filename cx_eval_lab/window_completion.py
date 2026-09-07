"""Diagnostic join of trusted-local registered membership and observed evidence.

Journal and campaign reads are separate transactions, not one cross-database
snapshot. Workers are not fenced by reading. This is neither a controller input
nor a baseline comparison, and never grants deployment authority.
"""

from dataclasses import asdict

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.exposure_study import FaultInjectedCandidate, case_from_plan
from cx_eval_lab.models import RefundWorldSeed


def _world_observations(campaign, members):
    """Read every existing requested world in one transaction; never register."""
    results = {}
    with campaign._transaction() as db:
        for member in members:
            worlds = []
            for order in member['case']['orders']:
                namespace = canonical_hash((member['candidate_namespace'], order['order_id']))
                exists = db.execute('SELECT 1 FROM worlds WHERE namespace=?', (namespace,)).fetchone()
                if exists is None:
                    worlds.append({'order_id': order['order_id'], 'evidence_present': False})
                    continue
                seed = RefundWorldSeed(customer_id=order['customer_id'], order_id=order['order_id'],
                    amount_cents=order['amount_cents'], currency=order['currency'], eligible=order['eligible'],
                    approval_threshold_cents=10000, simulate_timeout_after_commit=False)
                state, events = campaign._load(db, namespace, seed)
                worlds.append({'order_id': order['order_id'], 'evidence_present': True,
                    'state': {**asdict(state), 'refund_transaction_count': state.refund_transaction_count},
                    'events': [event.to_dict() for event in events]})
            results[member['candidate_namespace']] = worlds
    return results


def inspect_window(registry, journal, namespace, number, *, manifest_digest):
    """Retain planned denominator and unknown labels without executing agents."""
    registry.require_campaign(journal.campaign)
    journal.require_campaign(registry.campaign)
    plan = registry.inspect(namespace, number)
    if plan is None:
        raise ValueError('registered window required')
    if plan['manifest_digest'] != manifest_digest:
        raise ValueError('window manifest conflict')
    selected = [member for member in plan['members'] if member['served'] == 'candidate']
    saved = journal.inspect_many([{'namespace': member['candidate_namespace'],
        'case': case_from_plan(member['case']), 'agent': FaultInjectedCandidate.name,
        'reverse': False, 'manifest_digest': manifest_digest} for member in selected])
    records = {row['namespace']: row for row in saved}
    worlds = _world_observations(journal.campaign, selected)
    members = []
    for member in plan['members']:
        row = {**member, 'status': 'out_of_scope', 'candidate_pass': None,
               'observed_wrong_order_violation': None, 'artifact': None, 'worlds': [], 'worker_liveness': 'unknown'}
        if member['served'] == 'candidate':
            record = records[member['candidate_namespace']]
            observations = worlds[member['candidate_namespace']]
            artifact = record['artifact']
            if artifact is not None and type(artifact.get('passed')) is not bool:
                raise ValueError('completed candidate pass must be boolean')
            wrong = any(world['evidence_present'] and world['order_id'] != member['case']['expected_order_id']
                        and world['state']['refund_transaction_count'] > 0 for world in observations)
            complete = all(world['evidence_present'] for world in observations)
            row = {**row, 'status': {'missing': 'no_completion_record', 'started': 'no_completion',
                                    'completed': 'completed'}[record['status']],
                'candidate_pass': None if artifact is None else artifact['passed'],
                'observed_wrong_order_violation': True if wrong else False if complete else None,
                'artifact': artifact, 'worlds': observations,
                'world_evidence_complete': complete,
                'status_scope': 'completion_journal_observation_not_worker_liveness'}
        members.append(row)
    return {'authority': 'lab_only', 'deployment_authorized': False, 'plan': plan, 'members': members,
        'planned_served': len(selected),
        'completed_evidence': sum(row['status'] == 'completed' for row in members),
        'demonstrated_passes': sum(row['candidate_pass'] is True for row in members),
        'snapshot_semantics': 'separate_registry_journal_campaign_transactions_no_cross_database_atomicity',
        'baseline_comparison_available': False, 'controller_decision': None}
