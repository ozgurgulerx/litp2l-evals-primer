"""Run exposure transitions against isolated deterministic customer/order worlds."""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.exposure_control import (
    ExposureState,
    ExposureWindow,
    Observation,
    route,
    transition,
)
from cx_eval_lab.models import AgentOutput
from cx_eval_lab.order_resolution import (
    DescriptiveResolver,
    FirstRecordResolver,
    OrderRecord,
    ResolutionCase,
    UnresolvedRequest,
    _validate_backends,
    example_cases,
    run_case,
)


class FaultInjectedCandidate:
    """One fixed test harness; fault_mode is a declared experimental intervention."""

    name = 'fault-injected-candidate'

    def __init__(self, fault_mode):
        if fault_mode not in {'healthy', 'unavailable', 'wrong_order'}:
            raise ValueError('unknown study fault')
        self.fault_mode = fault_mode

    def run(self, request, tools):
        if self.fault_mode == 'unavailable':
            return AgentOutput(message='Service unavailable; no refund was issued.',
                               claimed_outcome='needs_review')
        agent = FirstRecordResolver() if self.fault_mode == 'wrong_order' else DescriptiveResolver()
        return agent.run(request, tools)


def build_window_plan(state, number, fault_mode, *, immature=False,
                      execution_namespace=None, manifest_digest=None, effect_backend=None):
    """Pure fixed-cohort selection shared by registered and legacy execution."""
    if type(number) is not int or number <= 0 or type(immature) is not bool:
        raise ValueError('positive integer window number and boolean maturity flag required')
    if not isinstance(state, ExposureState):
        raise TypeError('validated exposure predecessor required')
    FaultInjectedCandidate(fault_mode)
    _validate_backends(None, None, execution_namespace)
    if effect_backend not in (None, 'memory', 'durable'):
        raise ValueError('unknown effect backend')
    start, end = (number - 1) * 10, number * 10
    members = []
    for index in range(40):
        customer = f'user-{index}'
        base = example_cases()[0]
        case = replace(base, case_id=f'window-{number}-{customer}',
                       request=replace(base.request, customer_id=customer),
                       orders=tuple(replace(order, customer_id=customer)
                                    if order.customer_id == base.request.customer_id else order
                                    for order in base.orders))
        served = route(state, customer, now=start)
        execute = state.stage == 'shadow' or served == 'candidate'
        scope = ('served_candidate_durable_campaign' if served == 'candidate' and effect_backend == 'durable'
                 else 'served_candidate_campaign' if served == 'candidate'
                 else 'isolated_shadow' if execute else 'not_executed')
        members.append({'customer_id': customer, 'case': asdict(case), 'served': served,
                        'candidate_execute': execute,
                        'candidate_namespace': (canonical_hash((execution_namespace, number, customer))
                                                if execution_namespace is not None else None),
                        'effect_scopes': {'baseline': 'isolated_baseline_counterfactual', 'candidate': scope}})
    return json.loads(json.dumps({'schema': 1, 'predecessor': asdict(state), 'number': number,
        'start': start, 'end': end, 'fault_mode': fault_mode, 'immature': immature,
        'execution_namespace': execution_namespace, 'manifest_digest': manifest_digest,
        'effect_backend': effect_backend, 'members': members}, allow_nan=False))


def case_from_plan(value):
    return ResolutionCase(**{**value, 'request': UnresolvedRequest(**value['request']),
                             'orders': tuple(OrderRecord(**row) for row in value['orders'])})


def execute_window(state, number, fault_mode, *, immature=False, action_budget=None,
                   execution_namespace=None, durable_campaign=None, window_registry=None,
                   manifest_digest=None, completion_journal=None):
    _validate_backends(action_budget, durable_campaign, execution_namespace)
    if (window_registry is None) != (manifest_digest is None):
        raise ValueError('window registry and explicit manifest must be supplied together')
    if window_registry is not None and durable_campaign is None:
        raise ValueError('registered windows require a durable campaign')
    if completion_journal is not None:
        if window_registry is None or durable_campaign is None:
            raise ValueError('completion journal requires registered durable windows')
        window_registry.require_campaign(completion_journal.campaign)
        completion_journal.require_campaign(durable_campaign)
    if durable_campaign is not None:
        durable_campaign.snapshot()  # Verify storage even for shadow/baseline-only windows.
    plan = build_window_plan(state, number, fault_mode, immature=immature,
        execution_namespace=execution_namespace, manifest_digest=manifest_digest,
        effect_backend='durable' if durable_campaign is not None else 'memory' if action_budget is not None else None)
    if window_registry is not None:
        window_registry.require_campaign(durable_campaign)
        plan = window_registry.register(plan)
    start, end = plan['start'], plan['end']
    artifacts, observations = [], []
    candidate_count = 0
    for member in plan['members']:
        customer, served = member['customer_id'], member['served']
        case = case_from_plan(member['case'])
        candidate_count += served == 'candidate'
        baseline = run_case(case, DescriptiveResolver())
        candidate = (completion_journal.execute(case, FaultInjectedCandidate(fault_mode),
                        namespace=member['candidate_namespace'], manifest_digest=manifest_digest)
                     if completion_journal is not None and served == 'candidate' else
                     run_case(case, FaultInjectedCandidate(fault_mode),
                             action_budget=action_budget if served == 'candidate' else None,
                             durable_campaign=durable_campaign if served == 'candidate' else None,
                             execution_namespace=member['candidate_namespace'])
                     if member['candidate_execute'] else None)
        artifact = {'customer_id': customer, 'served': served,
                    'baseline': baseline, 'candidate': candidate,
                    'fault_intervention': fault_mode}
        if action_budget is not None or durable_campaign is not None:
            artifact = {**artifact, 'effect_scopes': member['effect_scopes']}
        artifacts.append(artifact)
        if candidate is not None:
            observations.append(Observation(customer, baseline['passed'], candidate['passed'],
                                            candidate['wrong_order_commits'] > 0,
                                            end + 50 if immature else end, canonical_hash(artifact)))
    window = ExposureWindow(f'window-{number}', state.candidate, state.baseline,
                            state.revision, start, end, tuple(observations))
    return window, artifacts, candidate_count


def run_study():
    state = ExposureState('cx-simulation-v1', 'baseline-v1')
    windows = []
    for number, (fault, resume) in enumerate((('healthy', False), ('healthy', False),
            ('unavailable', False), ('healthy', False), ('healthy', True),
            ('wrong_order', False), ('healthy', True)), start=1):
        window, artifacts, count = execute_window(state, number, fault, immature=fault == 'wrong_order')
        decision = transition(state, window, now=window.end, resume=resume)
        windows.append({'before': asdict(state), 'window': asdict(window),
                        'decision': asdict(decision), 'resume_requested': resume,
                        'served_candidate': count, 'served_baseline': 40 - count,
                        'artifacts': artifacts, 'artifact_hashes': [canonical_hash(row) for row in artifacts]})
        state = decision.state
    return {'study': 'exposure-control-v1', 'evidence_kind': 'executed_mock_traffic_simulation',
            'deployment_authorized': False, 'windows': windows,
            'source_hashes': {name: canonical_hash(Path('cx_eval_lab', name).read_text()) for name in
                              ('exposure_study.py', 'exposure_control.py', 'order_resolution.py',
                               'world.py', 'agents.py')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Refuse overwrite before executing the potentially larger study.
    if args.output.exists():
        parser.exit(2, 'Choose a new artifact path.\n')
    report = run_study()
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
