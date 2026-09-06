"""Finite-frame stratified SRSWOR study: exact design arithmetic, no model calls."""

import argparse
import itertools
import json
import math
import re
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _clone(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _fields(value, keys):
    _require(isinstance(value, dict) and set(value) == set(keys), 'exact schema fields required')


def _integer(value, lower, upper):
    value_type = type(value)
    _require(value_type is int and lower <= value <= upper, 'bounded exact integer required')


def _number(value, lower=0, upper=1):
    _require(not isinstance(value, bool) and isinstance(value, (int, float))
             and math.isfinite(value) and lower <= value <= upper, 'finite numeric probability required')
    return Fraction(str(value))


def _identifier(value):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value), 'opaque identifier required')


def _frame(frame, allocation):
    _require(isinstance(frame, list) and 1 <= len(frame) <= 32, 'bounded nonempty frame required')
    for row in frame:
        _fields(row, ('unit_id', 'stratum'))
        _identifier(row['unit_id'])
        _identifier(row['stratum'])
    lookup = {r['unit_id']: r['stratum'] for r in frame}
    _require(len(lookup) == len(frame), 'duplicate frame unit')
    sizes = dict(sorted(Counter(lookup.values()).items()))
    _fields(allocation, sizes)
    for h, size in sizes.items():
        _integer(allocation[h], 1, size)
    _require(len(sizes) <= 3, 'at most three teaching strata supported')
    return lookup, sizes


def _choose(n, k):
    return math.comb(n, k) if 0 <= k <= n else 0


def _mass(size, failures, sample, observed):
    return _choose(failures, observed) * _choose(size - failures, sample - observed)


@lru_cache(maxsize=8192)
def _bounds(size, sample, observed, tail):
    denominator = math.comb(size, sample)
    retained = [m for m in range(size + 1)
        if Fraction(sum(_mass(size, m, sample, j) for j in range(observed + 1)), denominator) > tail
        and Fraction(sum(_mass(size, m, sample, j) for j in range(observed, sample + 1)), denominator) > tail]
    return min(retained), max(retained)


def count_interval(sizes, allocation, failures, alpha=.05):
    """Invert both inclusive hypergeometric tails, with Bonferroni across strata."""
    _require(isinstance(sizes, dict) and 1 <= len(sizes) <= 3, 'bounded stratum sizes required')
    _fields(allocation, sizes)
    _fields(failures, sizes)
    level = _number(alpha)
    _require(0 < level < 1, 'alpha must be strictly between zero and one')
    bounds = {}
    for h, size in sorted(sizes.items()):
        _integer(size, 1, 32)
        _integer(allocation[h], 1, size)
        _integer(failures[h], 0, allocation[h])
        bounds[h] = _bounds(size, allocation[h], failures[h], level / (2 * len(sizes)))
    total = sum(sizes.values())
    return {'lower': float(Fraction(sum(v[0] for v in bounds.values()), total)),
        'upper': float(Fraction(sum(v[1] for v in bounds.values()), total)),
        'stratum_failure_count_bounds': {h: list(v) for h, v in bounds.items()},
        'confidence_level': float(1 - level),
        'method': 'hypergeometric-inclusive-tail-inversion-bonferroni',
        'tail_rule': 'retain both inclusive tail probabilities strictly greater than alpha/(2H)'}


def _decision(raw, weighted, interval, threshold):
    return {'raw_point': 'illustrative_clear' if raw <= threshold else 'illustrative_block',
        'weighted_point': 'illustrative_clear' if weighted <= threshold else 'illustrative_block',
        'interval': 'clear' if Fraction(str(interval['upper'])) <= threshold else
                    'block' if Fraction(str(interval['lower'])) > threshold else 'hold'}


def _estimate_counts(sizes, allocation, failures, alpha, threshold):
    total = sum(sizes.values())
    raw = Fraction(sum(failures.values()), sum(allocation.values()))
    weighted = sum((Fraction(sizes[h] * failures[h], allocation[h] * total) for h in sizes), Fraction())
    interval = count_interval(sizes, allocation, failures, alpha)
    return {'raw_failure_rate': float(raw), 'ht_failure_rate': float(weighted),
        'stratum_weighted_failure_rate': float(weighted),
        'raw_exact': str(raw), 'ht_exact': str(weighted), 'interval': interval,
        'threshold': float(threshold), 'decisions': _decision(raw, weighted, interval, threshold),
        'strata': {h: {'population_size': sizes[h], 'sample_size': allocation[h],
            'sample_failures': failures[h], 'pi': allocation[h] / sizes[h],
            'population_weight': sizes[h] / total} for h in sizes}}


def estimate_sample(frame, allocation, rows, alpha=.05, threshold=.35):
    """Only selected labels enter this estimator; frame contains IDs and strata only."""
    lookup, sizes = _frame(frame, allocation)
    threshold = _number(threshold)
    _require(isinstance(rows, list) and len(rows) == sum(allocation.values()), 'complete allocated sample required')
    labels, counts, weights = {}, Counter(), []
    for row in rows:
        _fields(row, ('unit_id', 'stratum', 'failure', 'pi'))
        _identifier(row['unit_id'])
        _require(row['unit_id'] in lookup and lookup[row['unit_id']] == row['stratum'], 'sample/frame join mismatch')
        _require(row['unit_id'] not in labels, 'duplicate sampled unit')
        label_type = type(row['failure'])
        _require(label_type is bool, 'observed label must be boolean; missing is not negative')
        pi = Fraction(allocation[row['stratum']], sizes[row['stratum']])
        _number(row['pi'])
        _require(row['pi'] == float(pi), 'pi must match positive registered stratum allocation')
        labels = {**labels, row['unit_id']: row['failure']}
        counts.update([row['stratum']])
        weights = [*weights, {'unit_id': row['unit_id'], 'inverse_pi': float(1 / pi),
            'ht_contribution': float(Fraction(int(row['failure']), len(frame)) / pi)}]
    _require(dict(counts) == allocation, 'sample stratum counts differ from allocation')
    failures = {h: sum(labels[r['unit_id']] for r in rows if r['stratum'] == h) for h in sizes}
    result = _estimate_counts(sizes, allocation, failures, alpha, threshold)
    ht = sum((Fraction(int(r['failure']), len(frame)) / Fraction(allocation[r['stratum']], sizes[r['stratum']])
              for r in rows), Fraction())
    _require(ht == Fraction(result['ht_exact']), 'HT/stratum weighted identity failed')
    return {**result, 'row_weights': weights, 'estimand': 'per-request failure fraction in this finite frame',
        'deployment_authorized': False}


def example_inputs():
    frame = [{'unit_id': f'{h}-{i}', 'stratum': h} for h, n in (('routine', 12), ('risk', 4)) for i in range(n)]
    return {'frame': frame,
        'outcomes': {r['unit_id']: r['unit_id'] in {'routine-0', 'risk-0', 'risk-1', 'risk-2'} for r in frame},
        'allocations': {'proportional': {'routine': 6, 'risk': 2}, 'enriched': {'routine': 4, 'risk': 4}},
        'alpha': .05, 'thresholds': [.35, .20], 'worked_design': 'enriched',
        'worked_ids': [f'risk-{i}' for i in range(4)] + [f'routine-{i}' for i in range(1, 5)]}


def _cells(sizes, allocation, population):
    strata = list(sizes)
    denominator = math.prod(math.comb(sizes[h], allocation[h]) for h in strata)
    for values in itertools.product(*(range(allocation[h] + 1) for h in strata)):
        failures = dict(zip(strata, values, strict=True))
        multiplicity = math.prod(_mass(sizes[h], population[h], allocation[h], failures[h]) for h in strata)
        if multiplicity:
            yield failures, multiplicity, denominator


def _qualification(sizes, allocation, alpha):
    records = []
    for values in itertools.product(*(range(s + 1) for s in sizes.values())):
        population = dict(zip(sizes, values, strict=True))
        truth = Fraction(sum(values), sum(sizes.values()))
        coverage = Fraction()
        for failures, multiplicity, denominator in _cells(sizes, allocation, population):
            interval = count_interval(sizes, allocation, failures, alpha)
            bounds = interval['stratum_failure_count_bounds'].values()
            lower = Fraction(sum(b[0] for b in bounds), sum(sizes.values()))
            upper = Fraction(sum(b[1] for b in bounds), sum(sizes.values()))
            if lower <= truth <= upper:
                coverage += Fraction(multiplicity, denominator)
        records = [*records, {'population_failures': population, 'coverage': float(coverage), 'coverage_exact': str(coverage)}]
    minimum = min(Fraction(r['coverage_exact']) for r in records)
    return {'population_count': len(records), 'minimum_coverage': float(minimum),
        'minimum_coverage_exact': str(minimum),
        'worst_populations': [r['population_failures'] for r in records if Fraction(r['coverage_exact']) == minimum],
        'populations': records, 'scope': 'all binary count populations for these fixed sizes/allocation/alpha only'}


def _distribution(sizes, allocation, population, alpha, thresholds):
    cells = []
    truth = Fraction(sum(population.values()), sum(sizes.values()))
    for failures, multiplicity, denominator in _cells(sizes, allocation, population):
        estimate = _estimate_counts(sizes, allocation, failures, alpha, _number(thresholds[0]))
        decisions = {str(t): _decision(Fraction(estimate['raw_exact']), Fraction(estimate['ht_exact']),
                                       estimate['interval'], _number(t)) for t in thresholds}
        cells = [*cells, {'failures': failures, 'multiplicity': multiplicity,
            'probability': float(Fraction(multiplicity, denominator)), 'probability_exact': str(Fraction(multiplicity, denominator)),
            'estimate': estimate, 'threshold_decisions': decisions}]
    def expectation(fn):
        return sum((Fraction(c['probability_exact']) * fn(c) for c in cells), Fraction())
    raw = expectation(lambda c: Fraction(c['estimate']['raw_exact']))
    weighted = expectation(lambda c: Fraction(c['estimate']['ht_exact']))
    coverage = expectation(lambda c: int(c['estimate']['interval']['lower'] <= float(truth) <= c['estimate']['interval']['upper']))
    outcomes = {str(t): {metric: {state: float(expectation(lambda c: int(c['threshold_decisions'][str(t)][metric] == state)))
        for state in (('clear', 'hold', 'block') if metric == 'interval' else ('illustrative_clear', 'illustrative_block'))}
        for metric in ('raw_point', 'weighted_point', 'interval')} for t in thresholds}
    return {'sample_set_count': sum(c['multiplicity'] for c in cells), 'cells': cells,
        'summary': {'expected_raw_failure_rate': float(raw), 'expected_ht_failure_rate': float(weighted),
            'raw_mse': float(expectation(lambda c: (Fraction(c['estimate']['raw_exact']) - truth) ** 2)),
            'ht_mse': float(expectation(lambda c: (Fraction(c['estimate']['ht_exact']) - truth) ** 2)),
            'interval_coverage': float(coverage), 'threshold_outcome_probabilities': outcomes,
            'false_clear_probabilities': {str(t): {metric: values.get('clear', values.get('illustrative_clear', 0))
                if truth > _number(t) else None for metric, values in outcomes[str(t)].items()} for t in thresholds}},
        'qualification': _qualification(sizes, allocation, alpha)}


def run_study(inputs=None):
    owned = _clone(example_inputs() if inputs is None else inputs)
    _fields(owned, ('frame', 'outcomes', 'allocations', 'alpha', 'thresholds', 'worked_design', 'worked_ids'))
    _require(isinstance(owned['allocations'], dict) and 1 <= len(owned['allocations']) <= 4, 'bounded designs required')
    for name, plan in owned['allocations'].items():
        _identifier(name)
        _frame(owned['frame'], plan)
    first = next(iter(owned['allocations'].values()))
    lookup, sizes = _frame(owned['frame'], first)
    _require(math.prod(s + 1 for s in sizes.values()) <= 1000, 'bounded count-population qualification required')
    _fields(owned['outcomes'], lookup)
    _require(all(isinstance(y, bool) for y in owned['outcomes'].values()), 'complete fixed boolean population labels required')
    thresholds = owned['thresholds']
    _require(isinstance(thresholds, list) and 1 <= len(thresholds) <= 5, 'registered thresholds required')
    for t in thresholds:
        _number(t)
    _require(len(set(thresholds)) == len(thresholds), 'duplicate threshold')
    alpha = _number(owned['alpha'])
    _require(0 < alpha < 1, 'alpha must be inside (0,1)')
    _require(owned['worked_design'] in owned['allocations'], 'unknown worked design')
    _require(isinstance(owned['worked_ids'], list) and all(i in lookup for i in owned['worked_ids']), 'unknown worked unit')
    protocol = {'design': 'independent stratified simple random sampling without replacement',
        'estimand': 'per-request fixed finite-frame failure fraction', 'label_semantics': 'fixed boolean failure',
        'interval': 'inclusive hypergeometric inversion; exclude tails <= alpha/(2H)',
        'point_rules': 'illustrative only; no promotion authority', 'qualification': 'all count populations at registered sizes'}
    registration = canonical_hash({'inputs': owned, 'protocol': protocol})
    population = {h: sum(owned['outcomes'][i] for i in lookup if lookup[i] == h) for h in sizes}
    plan = owned['allocations'][owned['worked_design']]
    rows = [{'unit_id': i, 'stratum': lookup[i], 'failure': owned['outcomes'][i], 'pi': plan[lookup[i]] / sizes[lookup[i]]}
            for i in owned['worked_ids']]
    worked = estimate_sample(owned['frame'], plan, rows, owned['alpha'], thresholds[0])
    report = {'schema': 'finite-stratified-sampling-v1', 'inputs': owned, 'protocol': protocol,
        'registration_hash': registration, 'truth': sum(population.values()) / len(lookup),
        'worked_example': {'design': owned['worked_design'], 'rows': rows, 'estimate': worked,
                           'selection_kind': 'hand-selected teaching realization, not a random draw'},
        'designs': {name: _distribution(sizes, allocation, population, owned['alpha'], thresholds)
                    for name, allocation in owned['allocations'].items()},
        'deployment_authorized': False,
        'limitations': 'Finite fixed frame and fixed labels, not new agent observations or deployment authority. '
            'Compression enumerates sample sets by outcome multiplicity. Missing labels/probabilities fail closed. '
            'No adaptive sampling, noisy-label correction, model inference, human qualification, temporal transfer '
            'or population outside this frame. Overall weighting cannot override separate hard risk constraints. '
            'Local input binding and re-execution do not authenticate historical preregistration.'}
    return {**report, 'report_hash': canonical_hash(report)}


def replay_study(report):
    owned = _clone(report)
    _require(isinstance(owned, dict) and 'inputs' in owned, 'retained study inputs required')
    expected = run_study(owned['inputs'])
    _require(canonical_hash(owned) == canonical_hash(expected), 'retained study differs from complete re-execution')
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    with args.output.open('x') as stream:
        stream.write(json.dumps(run_study(), indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
