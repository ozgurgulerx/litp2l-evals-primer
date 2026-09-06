"""Analyze supplied synthetic annotations; neither agreement nor assignment is human proof."""

import argparse
import itertools
import json
import math
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.statistical_study import exact_loss_interval

LABELS = ('pass', 'fail', 'unknown')
SOURCE = 'evals/cx-support/examples/human-annotations-v1.json'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(value, keys):
    _require(isinstance(value, dict) and set(value) == set(keys), 'exact schema fields required')


def _identifier(value):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value), 'opaque identifier required')


def _label(value, *, missing=True):
    _require((missing and value is None) or (isinstance(value, str) and value in LABELS), 'invalid annotation label')


def _clone(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _pairs(pairs):
    _require(isinstance(pairs, list) and len(pairs) <= 8, 'at most eight paired teaching items supported')
    for row in pairs:
        _fields(row, ('item_id', 'left', 'right'))
        _identifier(row['item_id'])
        _label(row['left'])
        _label(row['right'])
    _require(len({r['item_id'] for r in pairs}) == len(pairs), 'duplicate paired item')
    return [r for r in pairs if r['left'] is not None and r['right'] is not None]


def _kappa(counts):
    n = sum(counts.values())
    if not n:
        return None, None, None
    left = {c: sum(v for (a, _), v in counts.items() if a == c) for c in LABELS}
    right = {c: sum(v for (_, b), v in counts.items() if b == c) for c in LABELS}
    observed = Fraction(sum(v for (a, b), v in counts.items() if a == b), n)
    expected = Fraction(sum(left[c] * right[c] for c in LABELS), n * n)
    return observed, expected, None if expected == 1 else (observed - expected) / (1 - expected)


def _summary(rows, original_n, labels):
    counts = Counter((r['left'], r['right']) for r in rows)
    observed, expected, kappa = _kappa(counts)
    marginals = {side: {c: sum(r[side] == c for r in rows) for c in labels} for side in ('left', 'right')}
    return {'n': len(rows), 'item_ids': [r['item_id'] for r in rows],
        'item_coverage': len(rows) / original_n if original_n else None,
        'confusion': {a: {b: counts[(a, b)] for b in labels} for a in labels}, 'marginals': marginals,
        'observed_agreement': float(observed) if observed is not None else None,
        'expected_agreement': float(expected) if expected is not None else None,
        'expected_agreement_exact': str(expected) if expected is not None else None,
        'kappa': float(kappa) if kappa is not None else None,
        'kappa_exact': str(kappa) if kappa is not None else None,
        'pass_propensity_on_same_items': {side: marginals[side]['pass'] / len(rows) if rows else None
                                         for side in ('left', 'right')}}


def pair_metrics(pairs):
    complete = _pairs(pairs)
    binary = [r for r in complete if r['left'] != 'unknown' and r['right'] != 'unknown']
    interval = None
    if complete:
        lower, upper = exact_loss_interval(sum(r['left'] == r['right'] for r in complete), len(complete))
        interval = {'lower': lower, 'upper': upper, 'confidence_level': .95,
            'assumption': 'IID sampled paired items for agreement indicator; not a kappa interval',
            'fixture_does_not_establish_sampling': True, 'coverage_qualified_for_fixture': False}
    return {'full': _summary(complete, len(pairs), LABELS),
        'binary_decidable': {**_summary(binary, len(pairs), ('pass', 'fail')),
                            'estimand': 'agreement conditional on both ratings being pass or fail'},
        'missing_item_ids': [r['item_id'] for r in pairs if r not in complete],
        'missing_rating_count': sum(r[side] is None for r in pairs for side in ('left', 'right')),
        'unknown_item_ids': [r['item_id'] for r in pairs if 'unknown' in (r['left'], r['right'])],
        'unknown_rating_count': sum(r[side] == 'unknown' for r in pairs for side in ('left', 'right')),
        'agreement_interval_iid_assumption': interval}


def _compositions(total, slots):
    if slots == 1:
        yield (total,)
    else:
        for first in range(total + 1):
            for rest in _compositions(total - first, slots - 1):
                yield (first, *rest)


def bootstrap_pair(pairs):
    complete = _pairs(pairs)
    n = len(complete)
    cells = sorted(Counter((r['left'], r['right']) for r in complete).items())
    vectors, masses = [], Counter()
    if n:
        for vector in _compositions(n, len(cells)):
            multiplicity = math.factorial(n) // math.prod(math.factorial(k) for k in vector)
            multiplicity *= math.prod(count ** k for (_, count), k in zip(cells, vector, strict=True))
            counts = {pair: k for (pair, _), k in zip(cells, vector, strict=True)}
            kappa = _kappa(counts)[2]
            masses[kappa] += multiplicity
            vectors = [*vectors, {'counts': list(vector), 'multiplicity': multiplicity,
                                  'kappa_exact': str(kappa) if kappa is not None else None}]
    total = n ** n if n else 0
    distribution = [{'kappa_exact': str(k) if k is not None else None,
        'kappa': float(k) if k is not None else None, 'multiplicity': masses[k],
        'probability_exact': str(Fraction(masses[k], total)), 'probability': masses[k] / total}
        for k in sorted(masses, key=lambda k: (k is None, k or Fraction()))]
    finite = sorted((k, mass) for k, mass in masses.items() if k is not None)
    defined_total = sum(m for _, m in finite)
    def quantile(level):
        running = 0
        for k, mass in finite:
            running += mass
            if running >= level * defined_total:
                return k
        raise ValueError('empty defined bootstrap distribution')
    percentiles = None
    if defined_total:
        low, high = quantile(Fraction(1, 40)), quantile(Fraction(39, 40))
        percentiles = {'lower': float(low), 'upper': float(high), 'lower_exact': str(low), 'upper_exact': str(high),
            'conditioning': 'conditional_on_defined_kappa', 'quantile_rule': 'left inverse CDF at .025 and .975',
            'coverage_qualified': False, 'description': 'descriptive finite bootstrap percentile range, not a qualified CI'}
    return {'resampling_unit': 'whole paired item, not individual rating',
        'complete_item_ids': [r['item_id'] for r in complete], 'excluded_missing_item_ids': [r['item_id'] for r in pairs if r not in complete],
        'occupied_cells': [{'left': p[0], 'right': p[1], 'count': count} for p, count in cells],
        'count_vector_count': len(vectors), 'ordered_resample_count': total, 'count_vectors': vectors,
        'distribution': distribution, 'undefined_probability': masses[None] / total if total else None,
        'undefined_probability_exact': str(Fraction(masses[None], total)) if total else None,
        'percentiles': percentiles, 'sampling_claim': 'authored fixed items do not establish IID or population sampling'}


def _control_inputs():
    result = []
    for i in range(4):
        message = f'Authored identical baseline and candidate response for control case {i}.'
        output = {'message': message, 'content_hash': canonical_hash(message)}
        result = [*result, {'case_id': f'C{i + 1}', 'outputs': {a: dict(output) for a in ('baseline', 'candidate')},
            'ratings': {'strict': {a: 'pass' if i < 2 else 'fail' for a in ('baseline', 'candidate')},
                        'lenient': {a: 'pass' for a in ('baseline', 'candidate')}}}]
    return result


def example_inputs():
    fixture = json.loads((Path(__file__).resolve().parents[1] / SOURCE).read_text())
    rubric = 'resolution-explanation-v1'
    evidence = [{'item_id': item['case_id'], 'case_id': item['case_id'], 'rubric_version': rubric,
        'evidence_ref': f"synthetic-description/{item['case_id']}", 'evidence': dict(item),
        'evidence_hash': canonical_hash(item), 'evidence_kind': 'authored situation only; no supplied raw conversation'}
        for item in fixture['items']]
    return {'source': {'relative_path': SOURCE, 'content_hash': canonical_hash(fixture)},
        'source_fixture': fixture, 'rubric_version': rubric, 'raters': ['R1', 'R2', 'R3'],
        'item_evidence': evidence, 'bootstrap_pair': ['R1', 'R2'], 'assignment_control': _control_inputs()}


def _validate(inputs):
    _fields(inputs, ('source', 'source_fixture', 'rubric_version', 'raters', 'item_evidence', 'bootstrap_pair', 'assignment_control'))
    _fields(inputs['source'], ('relative_path', 'content_hash'))
    _require(inputs['source']['relative_path'] == SOURCE, 'source reference must name canonical fixture schema')
    source = inputs['source_fixture']
    _require(inputs['source']['content_hash'] == canonical_hash(source), 'source content hash mismatch')
    _fields(source, ('artifact_type', 'study_id', 'criterion', 'labels', 'items', 'annotations', 'adjudications', 'synthetic', 'release_evidence'))
    _require(source['artifact_type'] == 'synthetic_human_annotation_study' and source['synthetic'] is True
             and source['release_evidence'] is False and source['labels'] == list(LABELS), 'synthetic source schema required')
    _identifier(source['study_id'])
    _identifier(source['criterion'])
    _identifier(inputs['rubric_version'])
    raters = inputs['raters']
    _require(isinstance(raters, list) and len(raters) == 3 and len(set(raters)) == 3, 'three unique registered pseudonyms required')
    for rater in raters:
        _identifier(rater)
    _require(isinstance(source['items'], list) and 1 <= len(source['items']) <= 8, 'one to eight source items required')
    for item in source['items']:
        _fields(item, ('case_id', 'situation'))
        _identifier(item['case_id'])
        _require(isinstance(item['situation'], str) and 0 < len(item['situation']) <= 1000, 'bounded situation required')
    items = {i['case_id']: i for i in source['items']}
    _require(len(items) == len(source['items']), 'duplicate source case')
    _require(isinstance(inputs['item_evidence'], list) and len(inputs['item_evidence']) == len(items), 'complete evidence bindings required')
    evidence = {}
    for row in inputs['item_evidence']:
        _fields(row, ('item_id', 'case_id', 'rubric_version', 'evidence_ref', 'evidence', 'evidence_hash', 'evidence_kind'))
        item_id = row['item_id']
        _require(item_id in items and item_id not in evidence and row['case_id'] == item_id, 'bad item/case evidence join')
        _require(row['rubric_version'] == inputs['rubric_version'] and row['evidence'] == items[item_id]
            and row['evidence_hash'] == canonical_hash(row['evidence'])
            and row['evidence_ref'] == f'synthetic-description/{item_id}'
            and row['evidence_kind'] == 'authored situation only; no supplied raw conversation', 'evidence/rubric binding mismatch')
        evidence = {**evidence, item_id: row}
    _require(isinstance(source['annotations'], list), 'annotation records required')
    annotations = {}
    for row in source['annotations']:
        _fields(row, ('case_id', 'reviewer', 'label'))
        _require(row['case_id'] in items and row['reviewer'] in raters, 'foreign annotation join')
        _label(row['label'])
        key = (row['case_id'], row['reviewer'])
        _require(key not in annotations, 'duplicate annotation')
        annotations = {**annotations, key: row['label']}
    _require(set(annotations) == set(itertools.product(items, raters)), 'missing annotation slots must be explicit None')
    _require(isinstance(source['adjudications'], list), 'adjudication records required')
    adjudicated = set()
    for row in source['adjudications']:
        _fields(row, ('case_id', 'label', 'reason'))
        _require(row['case_id'] in items and row['case_id'] not in adjudicated, 'bad adjudication join')
        _label(row['label'], missing=False)
        _require(isinstance(row['reason'], str) and 0 < len(row['reason']) <= 1000, 'authored rationale required')
        adjudicated = adjudicated | {row['case_id']}
    pair = inputs['bootstrap_pair']
    _require(isinstance(pair, list) and len(pair) == 2 and pair[0] != pair[1] and all(r in raters for r in pair), 'registered distinct bootstrap pair required')
    return items, evidence, annotations


def _assignment(cases):
    _require(isinstance(cases, list) and len(cases) == 4, 'four authored assignment cases required')
    ids = set()
    for case in cases:
        _fields(case, ('case_id', 'outputs', 'ratings'))
        _identifier(case['case_id'])
        _require(case['case_id'] not in ids, 'duplicate assignment case')
        ids = ids | {case['case_id']}
        _fields(case['outputs'], ('baseline', 'candidate'))
        for output in case['outputs'].values():
            _fields(output, ('message', 'content_hash'))
            _require(isinstance(output['message'], str) and 0 < len(output['message']) <= 1000
                and output['content_hash'] == canonical_hash(output['message']), 'output content/hash mismatch')
        _require(case['outputs']['baseline'] == case['outputs']['candidate'], 'negative control requires identical arm outputs')
        _fields(case['ratings'], ('strict', 'lenient'))
        for ratings in case['ratings'].values():
            _fields(ratings, ('baseline', 'candidate'))
            _require(all(v in ('pass', 'fail') for v in ratings.values()) and ratings['baseline'] == ratings['candidate'],
                     'negative control requires binary arm-invariant potential ratings')
    designs = {}
    for design in ('confounded', 'crossed'):
        observations = [{'case_id': c['case_id'], 'arm': arm, 'reviewer': reviewer,
            'label': c['ratings'][reviewer][arm], 'output_hash': c['outputs'][arm]['content_hash']}
            for c in cases for arm in ('baseline', 'candidate') for reviewer in ('strict', 'lenient')
            if design == 'crossed' or (arm, reviewer) in (('baseline', 'strict'), ('candidate', 'lenient'))]
        rates = {a: sum(r['label'] == 'pass' for r in observations if r['arm'] == a)
                    / sum(r['arm'] == a for r in observations) for a in ('baseline', 'candidate')}
        designs[design] = {'observations': observations, 'pass_rates': rates,
            'candidate_minus_baseline': rates['candidate'] - rates['baseline'],
            'case_count': len(cases), 'rating_count': len(observations)}
    return {**designs, 'potential_ratings': cases,
        'per_reviewer_paired_gaps': {r: sum((c['ratings'][r]['candidate'] == 'pass') - (c['ratings'][r]['baseline'] == 'pass')
                                          for c in cases) / len(cases) for r in ('strict', 'lenient')},
        'matched_panel_pass_rates': {r: sum(c['ratings'][r]['baseline'] == 'pass' for c in cases) / len(cases) for r in ('strict', 'lenient')},
        'interpretation': 'authored assignment negative control, not real reviewer severity or randomized human experiment',
        'resampling_unit_if_extended': 'case with all arm/reviewer ratings, not individual rating'}


def run_study(inputs=None):
    owned = _clone(example_inputs() if inputs is None else inputs)
    items, evidence, annotations = _validate(owned)
    protocol = {'labels': list(LABELS), 'missing': 'None excludes affected pair only, with explicit denominator',
        'bootstrap': 'exact item-level empirical bootstrap; finite kappa percentiles conditional on defined values',
        'assignment': 'authored full potential table, confounded and crossed deterministic observation selectors',
        'authority': 'synthetic annotation analysis only'}
    registration = canonical_hash({'inputs': owned, 'protocol': protocol})
    pairs = {f'{left}:{right}': [{'item_id': i, 'left': annotations[(i, left)], 'right': annotations[(i, right)]} for i in items]
             for left, right in itertools.combinations(owned['raters'], 2)}
    left, right = owned['bootstrap_pair']
    bootstrap_rows = [{'item_id': i, 'left': annotations[(i, left)], 'right': annotations[(i, right)]} for i in items]
    adjudications = []
    for record in owned['source_fixture']['adjudications']:
        case_id = record['case_id']
        binding = {'item_evidence': evidence[case_id], 'rubric_version': owned['rubric_version'],
            'original_annotations': [r for r in owned['source_fixture']['annotations'] if r['case_id'] == case_id]}
        adjudications = [*adjudications, {'original': record, 'binding': binding,
            'binding_hash': canonical_hash(binding), 'kind': 'supplied authored adjudication, not independent verification'}]
    report = {'schema': 'synthetic-rater-study-v1', 'inputs': owned, 'protocol': protocol,
        'registration_hash': registration, 'pair_metrics': {key: pair_metrics(rows) for key, rows in pairs.items()},
        'registered_pair_bootstrap': {'raters': [left, right], **bootstrap_pair(bootstrap_rows)},
        'adjudication_records': adjudications, 'assignment_control': _assignment(owned['assignment_control']),
        'deployment_authorized': False, 'evidence_kind': 'synthetic_annotation_analysis',
        'limitations': 'Original supplied labels and four authored adjudications are preserved. Situation descriptors '
            'are not full conversations or independent truth. Agreement and pass propensity are not accuracy. '
            'The bootstrap preserves item pairs but does not establish population coverage; undefined draws are '
            'reported separately. Binary projection conditions on decidability. Binomial agreement bounds assume '
            'IID sampled paired items; this authored fixture does not establish that sampling. Assignment outputs '
            'and all potential ratings are deliberately constructed, not collected from humans or agents. '
            'Hashes establish local content binding, not authenticated provenance or historical registration.'}
    return {**report, 'report_hash': canonical_hash(report)}


def replay_study(report):
    owned = _clone(report)
    _require(isinstance(owned, dict) and 'inputs' in owned, 'retained inputs required')
    expected = run_study(owned['inputs'])
    _require(canonical_hash(owned) == canonical_hash(expected), 'retained study differs from reanalysis')
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
