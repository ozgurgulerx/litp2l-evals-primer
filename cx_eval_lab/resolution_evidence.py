"""Native multi-order evidence: mock-tool replay, not execution attestation."""

from dataclasses import asdict, dataclass
import json
import math

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import AgentOutput, CheckResult, MeasurementProfile, RuntimeEvidence
from cx_eval_lab.order_resolution import (
    MultiOrderWorld, OrderRecord, ResolutionCase, UnresolvedRequest, grade_resolution_execution,
)

SCHEMA = 'resolution-trial-v1'
DATASET = 'order-resolution-v1'
EVALUATOR = 'resolution-contract-v1'
ESTIMAND = 'candidate_minus_baseline_resolution_contract'
SLICES = ('journey:refund', 'surface:order-resolution')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def case_from_dict(raw):
    _require(isinstance(raw, dict) and isinstance(raw.get('orders'), (list, tuple))
             and 1 <= len(raw['orders']) <= 100, 'resolution case requires 1..100 orders')
    case = ResolutionCase(**{**raw, 'request': UnresolvedRequest(**raw['request']),
                              'orders': tuple(OrderRecord(**r) for r in raw['orders'])})
    _require(isinstance(case.case_id, str) and bool(case.case_id.strip()), 'invalid resolution case ID')
    _require(case.clarification_reply is None or isinstance(case.clarification_reply, str),
             'invalid clarification reply')
    _require(1 <= len(case.orders) <= 100, 'resolution case requires 1..100 orders')
    return case


def population_entry(case):
    return [case.case_id, case.request.customer_id, list(SLICES)]


def design(baseline, candidate, semantic_registration=None):
    return {'baseline_agent': baseline, 'candidate_agent': candidate,
            'order_permutation': 'reverse_on_odd_repetitions',
            'arm_order': 'alternate_by_case_and_repetition',
            'criterion': EVALUATOR, 'semantic_qualification':
                'not_implemented' if semantic_registration is None else semantic_registration}


def validate_registration(manifest, cases, registered_design):
    _require(cases and len({c.case_id for c in cases}) == len(cases), 'unique resolution cases required')
    _require(type(manifest.repetitions) is int and manifest.repetitions >= 2
             and manifest.repetitions % 2 == 0, 'balanced resolution repetitions require a positive even count')
    semantic = registered_design['semantic_qualification']
    native = isinstance(semantic, dict)
    evaluator, estimand = EVALUATOR, ESTIMAND
    if native:
        from cx_eval_lab import resolution_semantic as ns
        ns.validate_registration(semantic)
        evaluator, estimand = ns.EVALUATOR, ns.ESTIMAND
        _require(dict(manifest.input_hashes).get('native-semantic-registration') == canonical_hash(semantic),
                 'native semantic registration is not bound to manifest')
    _require(manifest.dataset_version == DATASET and manifest.evaluator_version == evaluator
             and manifest.estimand == estimand, 'resolution manifest scope mismatch')
    _require(registered_design == design(registered_design['baseline_agent'],
                                        registered_design['candidate_agent'], semantic if native else None),
             'unsupported resolution design')
    hashes = dict(manifest.input_hashes)
    _require(hashes.get('resolution-cases') == canonical_hash([asdict(c) for c in cases]),
             'registered resolution cases mismatch')
    _require(hashes.get('resolution-design') == canonical_hash(registered_design),
             'registered resolution design mismatch')
    _require(manifest.population_hash == canonical_hash([population_entry(c) for c in cases]),
             'registered resolution population mismatch')


def validate_packet(packet, manifest):
    artifacts = packet['trial_artifacts']
    schema = artifacts[0]['payload']['schema'] if artifacts else None
    _require(schema in {SCHEMA, 'resolution-trial-v2'}
             and all(a['payload']['schema'] == schema for a in artifacts),
             'mixed or unsupported resolution artifact schemas')
    by_hash = {a['artifact_hash']: a['payload'] for a in artifacts}
    _require(all(type(r['trial_index']) is int for arm in ('baseline', 'candidate')
                 for r in packet[arm + '_trials']), 'invalid resolution trial index')
    population = [case_from_dict(by_hash[r['artifact_hash']]['case'])
                  for r in packet['baseline_trials'] if r['trial_index'] == 0]
    first = artifacts[0]['payload']
    _require((schema == 'resolution-trial-v2') == isinstance(first['design']['semantic_qualification'], dict),
             'native semantic schema/design mismatch')
    validate_registration(manifest, population, first['design'])
    registered = {c.case_id: canonical_hash(asdict(c)) for c in population}
    expected_sequence = [(c.case_id, index, arm) for index in range(manifest.repetitions)
                         for position, c in enumerate(population)
                         for arm in (('candidate', 'baseline') if (index + position) % 2
                                     else ('baseline', 'candidate'))]
    actual_sequence = [(a['payload']['identity']['case_id'], a['payload']['identity']['trial_index'],
                        a['payload']['identity']['arm']) for a in artifacts]
    _require(actual_sequence == expected_sequence, 'resolution artifact execution order mismatch')
    for artifact in artifacts:
        p = artifact['payload']
        identity = p['identity']
        _require(canonical_hash(p['case']) == registered.get(identity['case_id']),
                 'resolution case changed between paired trials')
        _require(p['design'] == first['design'] and p['agent'] == p['design'][identity['arm'] + '_agent'],
                 'resolution arm configuration mismatch')
        _require(type(identity['trial_index']) is int and type(p['reverse']) is bool
                 and p['reverse'] == bool(identity['trial_index'] % 2), 'resolution schedule mismatch')
        _require(p['dataset_version'] == manifest.dataset_version
                 and p['measurement']['evidence_kind'] == manifest.measurement_kind,
                 'resolution dataset or measurement mismatch')


@dataclass(frozen=True)
class ResolutionEvaluation:
    case_id: str
    checks: tuple[CheckResult, ...]
    task_completed: bool
    latency_ms: int
    cost_usd: float | None
    metrics_json: str

    @property
    def passed(self):
        return all(c.passed for c in self.checks)

    @property
    def unqualified_message_count(self):
        return 1

    def to_dict(self):
        return {'case_id': self.case_id, 'checks': [c.to_dict() for c in self.checks],
                'passed': self.passed, 'task_completed': self.task_completed,
                'latency_ms': self.latency_ms, 'cost_usd': self.cost_usd,
                'metrics': json.loads(self.metrics_json), 'criterion': EVALUATOR,
                'unqualified_message_count': 1, 'semantic_message_qualified': False}


def evaluate_execution(payload):
    case = case_from_dict(payload['case'])
    data = payload['output']
    _require(isinstance(data, dict), 'resolution output must be an object')
    runtime = data.get('runtime_evidence')
    _require(runtime is None or isinstance(runtime, dict), 'resolution runtime must be an object')
    output = AgentOutput(**{**data, 'runtime_evidence': None if runtime is None else RuntimeEvidence(**runtime)})
    metrics = grade_resolution_execution(case, output, payload['orders'], payload['tool_events'],
                                         payload['execution_error'])
    checks = tuple(CheckResult(name, metrics[name] == 0, str(metrics[name])) for name in (
        'wrong_order_commits', 'unnecessary_clarifications', 'missing_clarifications',
        'denied_attempts', 'premature_action_attempts'))
    checks += (CheckResult('resolution_contract', metrics['passed'], 'structural outcome and response enum'),)
    return ResolutionEvaluation(case.case_id, checks, metrics['task_completed'], payload['latency_ms'],
                                payload['cost_usd'], json.dumps(metrics, sort_keys=True))


def _replay_tools(case, payload):
    world = MultiOrderWorld(case, payload['reverse'])
    tools = world.tools()
    # Explicit facade whitelist: evidence cannot invoke arbitrary Python members.
    methods = {name: getattr(tools, name) for name in (
        'list_orders', 'ask_customer', 'verify_identity', 'get_order', 'consult_refund_policy',
        'request_refund_approval', 'issue_refund', 'inspect_order_status')}
    events = payload['tool_events']
    _require(isinstance(events, list) and len(events) <= 1000, 'invalid resolution tool transcript')
    for event in events:
        _require(event['tool'] in methods and isinstance(event['arguments'], list),
                 'unsupported resolution tool or arguments')
        try:
            methods[event['tool']](*event['arguments'])
        except (ValueError, PermissionError):
            pass  # The recorded error must exactly match below, including its class.
        except (TypeError, IndexError, AttributeError) as error:
            raise ValueError('malformed resolution tool arguments') from error
        _require(world._events and canonical_hash(world._events[-1]) == canonical_hash(event),
                 'resolution tool replay differs from recorded result')
    _require(canonical_hash(world.artifacts()) == canonical_hash(payload['orders']),
             'resolution ledger replay differs from retained state')


def regrade(payload, trusted_calibration_hashes=frozenset()):
    case = case_from_dict(payload['case'])
    _require(payload['agent_input'] == asdict(case.request), 'resolution agent input mismatch')
    _require(type(payload['reverse']) is bool, 'invalid resolution permutation')
    native = payload['schema'] == 'resolution-trial-v2'
    if not native:
        _require(payload['semantic_message_qualified'] is False
                 and payload['semantic_evaluation_receipt'] is None
                 and payload['qualified_semantic_calibration_hashes'] == []
                 and payload['semantic_stage'] is None, 'native resolution semantic qualification unsupported')
    _require(payload['authority'] == 'lab_only', 'resolution execution authority mismatch')
    error = payload['execution_error']
    _require(error is None or isinstance(error, str) and error.isidentifier(),
             'resolution execution error must be an exception class name')
    _require(type(payload['latency_ms']) is int and payload['latency_ms'] >= 0,
             'invalid resolution latency')
    cost = payload['cost_usd']
    _require(cost is None or type(cost) in (int, float) and math.isfinite(cost) and cost >= 0,
             'invalid resolution cost')
    _validate_measurements(payload)
    _replay_tools(case, payload)
    result = evaluate_execution(payload)
    for key, value in json.loads(result.metrics_json).items():
        observed_key = 'structural_contract_passed' if native and key == 'passed' else key
        _require(canonical_hash(payload[observed_key]) == canonical_hash(value), 'resolution metrics mismatch')
    if native:
        from cx_eval_lab.resolution_semantic_replay import JointResolutionEvaluation, verify_semantics
        result = JointResolutionEvaluation(result, verify_semantics(payload, trusted_calibration_hashes))
        _require(payload['semantic_message_qualified'] is result.to_dict()['semantic_message_qualified'],
                 'native semantic qualification summary mismatch')
    return result


def _validate_measurements(payload):
    elapsed = payload['elapsed_ms']
    _require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0,
             'invalid resolution elapsed measurement')
    measurement = payload['measurement']
    _require(isinstance(measurement, dict), 'resolution measurement must be an object')
    if 'latency_ms' in measurement:
        profile = MeasurementProfile(**measurement)
        _require(profile.evidence_kind == 'synthetic', 'profile measurements must be synthetic')
        latency, cost = profile.latency_ms, profile.cost_usd_per_case
    else:
        _require(measurement == {'evidence_kind': 'measured', 'source': 'runner wall-clock; runtime usage'},
                 'unsupported resolution measurement source')
        _require(isinstance(payload['output'], dict), 'resolution output must be an object')
        runtime = payload['output'].get('runtime_evidence')
        _require(runtime is None or isinstance(runtime, dict), 'resolution runtime must be an object')
        latency, cost = round(elapsed), None if runtime is None else runtime['cost_usd']
    _require(canonical_hash([payload['latency_ms'], payload['cost_usd']]) == canonical_hash([latency, cost]),
             'resolution measurement differs from retained source')
