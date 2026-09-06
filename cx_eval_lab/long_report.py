"""Format-bound Finding extraction from complete reports, with authored semantic evidence."""

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash

SOURCE = 'docs/assets/long-report-inputs-v1.json'
CONTROLS = ('sentence', 'clause', 'cited-only')
STATUSES = ('supported', 'contradicted', 'unsupported', 'unknown')
MARKER = re.compile(r'\[([A-Za-z0-9_-]{1,80})\]')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(value, keys):
    _require(isinstance(value, dict) and set(value) == set(keys), 'exact registered schema required')


def _identifier(value):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value), 'opaque identifier required')


def _text(value):
    _require(isinstance(value, str) and 0 < len(value) <= 50000, 'bounded nonempty text required')


def _date(value):
    _require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'ISO date required')
    return date.fromisoformat(value)


def _unique(rows, key):
    _require(isinstance(rows, list) and len(rows) <= 100, 'bounded record list required')
    for row in rows:
        _require(isinstance(row, dict) and key in row, 'record identity required')
        _identifier(row[key])
    result = {r[key]: r for r in rows}
    _require(len(result) == len(rows), 'duplicate registered ID')
    return result


def _span(text, span):
    _fields(span, ('start', 'end', 'quote'))
    for value in (span['start'], span['end']):
        kind = type(value)
        _require(kind is int, 'span boundaries must be exact integers')
    _require(0 <= span['start'] < span['end'] <= len(text)
             and text[span['start']:span['end']] == span['quote'], 'span/quote mismatch')


def _windows(text):
    return list(re.finditer(r'^Finding: (.+)$', text, re.MULTILINE))


def extract_claims(text, control):
    """Only text and a named control enter; no gold IDs, support labels or source inventory."""
    _text(text)
    _require(control in CONTROLS, 'unknown extraction control')
    units = []
    for finding in _windows(text):
        raw = finding.group(1)
        segments = [re.match(r'.+', raw)] if control == 'sentence' else list(re.finditer(r'[^;]+', raw))
        for segment in segments:
            if segment is None:
                continue
            fragment = segment.group()
            markers = [m.group(1) for m in MARKER.finditer(fragment)]
            if control == 'cited-only' and not markers:
                continue
            right = fragment.rstrip().rstrip('.!?').rstrip()
            right = re.sub(r'(?:\s*\[[A-Za-z0-9_-]{1,80}\])+\s*$', '', right).rstrip()
            leading = len(right) - len(right.lstrip())
            quote = right.lstrip()
            if quote:
                start = finding.start(1) + segment.start() + leading
                units.append({'unit_id': f'unit-{len(units) + 1:03}',
                    'span': {'start': start, 'end': start + len(quote), 'quote': quote}, 'citation_ids': markers})
    return units


def example_inputs():
    return json.loads((Path(__file__).resolve().parents[1] / SOURCE).read_text())


def _validate_sources(inputs):
    _fields(inputs, ('schema', 'task', 'rubric', 'sources', 'reports'))
    _require(inputs['schema'] == 'long-report-inputs-v1', 'known input schema required')
    task = inputs['task']
    _fields(task, ('task_id', 'as_of', 'scope', 'questions', 'required_synthesis_ids'))
    _identifier(task['task_id'])
    _identifier(task['scope'])
    _date(task['as_of'])
    required_synthesis = task['required_synthesis_ids']
    _require(isinstance(required_synthesis, list) and required_synthesis, 'independent synthesis obligations required')
    for requirement in required_synthesis:
        _identifier(requirement)
    _require(len(required_synthesis) == len(set(required_synthesis)), 'duplicate synthesis obligation')
    questions = _unique(task['questions'], 'question_id')
    _require(bool(questions), 'required question inventory cannot disappear')
    for question in questions.values():
        _fields(question, ('question_id', 'text'))
        _text(question['text'])
    _fields(inputs['rubric'], ('version', 'text'))
    _identifier(inputs['rubric']['version'])
    _text(inputs['rubric']['text'])
    sources = _unique(inputs['sources'], 'source_id')
    _require(bool(sources), 'frozen sources required')
    for source in sources.values():
        _fields(source, ('source_id', 'title', 'text', 'authority', 'scope', 'published_at', 'effective_from', 'effective_until'))
        _text(source['title'])
        _text(source['text'])
        _require(source['authority'] == 'invented-policy-owner' and source['scope'] == task['scope'], 'source authority/scope mismatch')
        _require(_date(source['published_at']) <= _date(source['effective_from']), 'invalid publication/effective dates')
        if source['effective_until'] is not None:
            _require(_date(source['effective_from']) < _date(source['effective_until']), 'invalid effective range')
    reports = _unique(inputs['reports'], 'report_id')
    _require(len(reports) == 2, 'original and repaired report required')
    return questions, sources


def _validate_report(report, questions, sources, required_synthesis):
    _fields(report, ('report_id', 'text', 'claims', 'coverage', 'synthesis'))
    _text(report['text'])
    claims = _unique(report['claims'], 'claim_id')
    _require(bool(claims), 'authored atomic claim inventory required')
    windows = _windows(report['text'])
    _require(bool(windows), 'registered Finding paragraphs required')
    link_ids = []
    spans = []
    for claim in claims.values():
        _fields(claim, ('claim_id', 'span', 'kind', 'status', 'links', 'reason', 'question_ids', 'abstention_target_answerability'))
        _span(report['text'], claim['span'])
        _require(not MARKER.search(claim['span']['quote']), 'atomic spans must exclude citation trailers')
        spans.append((claim['span']['start'], claim['span']['end']))
        containers = [w for w in windows if w.start(1) <= claim['span']['start'] < claim['span']['end'] <= w.end(1)]
        _require(len(containers) == 1, 'gold atom outside registered Finding paragraph')
        _require(claim['kind'] in ('factual', 'recommendation', 'inference', 'abstention') and claim['status'] in STATUSES, 'explicit kind/status required')
        _require(claim['abstention_target_answerability'] == ('unknown' if claim['kind'] == 'abstention' else None),
                 'abstention target answerability is separate from assertion support')
        _text(claim['reason'])
        _require(isinstance(claim['question_ids'], list) and claim['question_ids']
            and len(set(claim['question_ids'])) == len(claim['question_ids']) and set(claim['question_ids']).issubset(questions), 'claim/question join mismatch')
        _require(isinstance(claim['links'], list), 'citation list required')
        for link in claim['links']:
            _fields(link, ('citation_id', 'source_id', 'source_span', 'relation'))
            _identifier(link['citation_id'])
            link_ids.append(link['citation_id'])
            occurrences = list(re.finditer(re.escape('[' + link['citation_id'] + ']'), report['text']))
            _require(len(occurrences) == 1, 'citation must occur exactly once')
            marker = occurrences[0]
            between = report['text'][claim['span']['end']:marker.start()]
            _require(claim['span']['end'] <= marker.start() < containers[0].end(1)
                and not re.search(r'[;.!?\n]', between), 'citation marker must trail its own atomic clause')
            if link['source_id'] is None:
                _require(link['source_span'] is None and link['relation'] == 'unresolved', 'unresolved link cannot supply support')
            else:
                _require(link['source_id'] in sources and link['relation'] in ('entails', 'contradicts', 'insufficient'), 'source/relation mismatch')
                _span(sources[link['source_id']]['text'], link['source_span'])
    _require(len(spans) == len(set(spans)), 'duplicate atomic span would double count')
    ordered_spans = sorted(spans)
    _require(all(left[1] <= right[0] for left, right in zip(ordered_spans, ordered_spans[1:])),
             'registered atomic clause spans must not intersect')
    _require(len(link_ids) == len(set(link_ids)) and sorted(link_ids) == sorted(m.group(1) for m in MARKER.finditer(report['text'])),
             'all literal citation attempts must join the complete inventory')
    # Independent inventory completeness check: all non-structural Finding text is covered.
    for window in windows:
        covered = set()
        for start, end in spans:
            covered.update(range(max(start, window.start(1)), min(end, window.end(1))))
        for marker in MARKER.finditer(report['text'], window.start(1), window.end(1)):
            covered.update(range(marker.start(), marker.end()))
        _require(all(i in covered or report['text'][i] in ' \t;.!?' for i in range(window.start(1), window.end(1))),
                 'unregistered material text remains in Finding paragraph')
    coverage = _unique(report['coverage'], 'question_id')
    _require(set(coverage) == set(questions), 'all required questions need explicit coverage records')
    for row in coverage.values():
        _fields(row, ('question_id', 'status', 'claim_ids', 'reason'))
        _text(row['reason'])
        _require(row['status'] in ('answered', 'partially_answered', 'omitted', 'justified_abstention'), 'unknown coverage status')
        _require(isinstance(row['claim_ids'], list) and len(set(row['claim_ids'])) == len(row['claim_ids'])
            and set(row['claim_ids']) == {k for k, c in claims.items() if row['question_id'] in c['question_ids']}, 'question coverage/claim map disagreement')
        _require((row['status'] == 'omitted') == (not row['claim_ids']), 'omission is not a supplied answer')
        if row['status'] == 'justified_abstention':
            _require(any(claims[k]['kind'] == 'abstention' and claims[k]['status'] == 'supported'
                and claims[k]['abstention_target_answerability'] == 'unknown' for k in row['claim_ids']),
                'justified abstention needs a supported statement about an unknown target')
    synthesis = _unique(report['synthesis'], 'synthesis_id')
    _require(set(synthesis) == set(required_synthesis), 'all task-registered synthesis obligations need explicit reviews')
    for row in synthesis.values():
        _fields(row, ('synthesis_id', 'claim_ids', 'evidence_claim_ids', 'status', 'reason'))
        _text(row['reason'])
        _require(row['status'] in (*STATUSES, 'omitted'), 'explicit synthesis status required')
        for key in ('claim_ids', 'evidence_claim_ids'):
            _require(isinstance(row[key], list) and (bool(row[key]) if row['status'] != 'omitted' else not row[key])
                and len(set(row[key])) == len(row[key])
                and set(row[key]).issubset(claims), 'synthesis claim/evidence join mismatch')
    return claims, windows


def _ratio(n, total):
    return {'numerator': n, 'denominator': total, 'rate': n / total if total else None}


def score_extraction(units, report):
    """Exact atomic spans define recovery; containing several atoms is not recovering them."""
    _unique(units, 'unit_id')
    seen = {}
    scored = []
    claims = report['claims']
    for unit in units:
        _fields(unit, ('unit_id', 'span', 'citation_ids'))
        _span(report['text'], unit['span'])
        key = (unit['span']['start'], unit['span']['end'])
        duplicate_of = seen.get(key)
        seen = {**seen, key: seen.get(key, unit['unit_id'])}
        exact = [c for c in claims if c['span'] == unit['span']]
        contained = [c['claim_id'] for c in claims if unit['span']['start'] <= c['span']['start'] and c['span']['end'] <= unit['span']['end']]
        scored.append({**unit, 'duplicate_of': duplicate_of, 'exact_claim_ids': [c['claim_id'] for c in exact], 'contained_claim_ids': contained,
            'status': exact[0]['status'] if len(exact) == 1 else 'unscored_nonatomic_or_unmatched',
            'semantic_binding_hash': canonical_hash(exact) if exact else None})
    recovered = {k for r in scored for k in r['exact_claim_ids']}
    gold_supported = {c['claim_id'] for c in claims if c['status'] == 'supported'}
    groups = [[c['claim_id'] for c in claims if w.start(1) <= c['span']['start'] and c['span']['end'] <= w.end(1)]
              for w in _windows(report['text'])]
    compound = [g for g in groups if len(g) > 1]
    return {'units': scored, 'extracted_unit_count': len(units),
        'atomic_recall': _ratio(len(recovered), len(claims)),
        'exact_unit_precision': _ratio(sum(bool(r['exact_claim_ids']) and r['duplicate_of'] is None for r in scored), len(units)),
        'duplicate_unit_count': sum(r['duplicate_of'] is not None for r in scored),
        'unscored_unit_count': sum(not r['exact_claim_ids'] for r in scored),
        'omitted_claim_ids': [c['claim_id'] for c in claims if c['claim_id'] not in recovered],
        'compound_groups': compound, 'compound_fully_recovered': _ratio(sum(set(g).issubset(recovered) for g in compound), len(compound)),
        'observed_support': _ratio(len(recovered & gold_supported), len(recovered)),
        'full_inventory_support': _ratio(len(gold_supported), len(claims)),
        'unknown_recovered_count': sum(c['status'] == 'unknown' and c['claim_id'] in recovered for c in claims),
        'abstention_target_unknown_recovered_count': sum(c.get('abstention_target_answerability') == 'unknown'
            and c['claim_id'] in recovered for c in claims),
        'score_scope': 'observed support conditions on exact-matched registered atoms; unmatched units remain unscored, omissions retain full recall denominator'}


def _report_analysis(report, sources, as_of, context):
    controls = {name: score_extraction(extract_claims(report['text'], name), report) for name in CONTROLS}
    source_bindings = []
    for claim in report['claims']:
        for link in claim['links']:
            source = sources.get(link['source_id'])
            current = None if source is None else (_date(source['published_at']) <= _date(as_of)
                and _date(source['effective_from']) <= _date(as_of)
                and (source['effective_until'] is None or _date(as_of) < _date(source['effective_until'])))
            source_bindings.append({'claim_id': claim['claim_id'], 'citation_id': link['citation_id'],
                'relation': link['relation'], 'current': current, 'binding_hash': canonical_hash({'claim': claim, 'link': link, 'source': source})})
    claims = {c['claim_id']: c for c in report['claims']}
    synthesis = [{**row, 'binding_hash': canonical_hash({'review': row,
        'claims': [claims[k] for k in row['claim_ids']], 'evidence_claims': [claims[k] for k in row['evidence_claim_ids']]})}
        for row in report['synthesis']]
    return {'report_id': report['report_id'], 'report_hash': canonical_hash(report), 'shared_context_hash': context,
        'word_count': len(report['text'].split()), 'gold_claim_count': len(claims), 'controls': controls,
        'gold_status_counts': {s: sum(c['status'] == s for c in claims.values()) for s in STATUSES},
        'underlying_unknown_count': sum(c['abstention_target_answerability'] == 'unknown' for c in claims.values()),
        'source_bindings': source_bindings, 'question_coverage': report['coverage'], 'synthesis': synthesis,
        'coverage_counts': dict(Counter(r['status'] for r in report['coverage'])),
        'synthesis_counts': dict(Counter(r['status'] for r in synthesis))}


def run_study(inputs=None):
    owned = json.loads(json.dumps(example_inputs() if inputs is None else inputs, allow_nan=False))
    questions, sources = _validate_sources(owned)
    for report in owned['reports']:
        _validate_report(report, questions, sources, owned['task']['required_synthesis_ids'])
    shared = canonical_hash({k: owned[k] for k in ('task', 'rubric', 'sources')})
    protocol = {'controls': list(CONTROLS), 'extraction_scope': 'registered single-line Finding paragraphs only; not surrounding prose or general NLP material-claim discovery',
        'span_unit': 'Unicode code points, end exclusive; exclude Finding prefix, final punctuation and citation trailers',
        'atomic_match': 'exact span identity only; enclosing compounds are one-to-many coverage, not atomic recovery',
        'semantic_authority': 'all status, question mapping and synthesis judgments supplied by the authored casebook',
        'abstention': 'assertion support is separate from unknown underlying target; nonabstention target answerability is not assessed',
        'gold_format': 'declared nonoverlapping Finding atoms; format compliance and casebook review, not general extraction qualification',
        'denominators': 'registered atomic inventory and required questions remain fixed under extraction omission'}
    registration = canonical_hash({'inputs': owned, 'protocol': protocol})
    analyses = [_report_analysis(r, sources, owned['task']['as_of'], shared) for r in owned['reports']]
    result = {'schema': 'long-report-study-v1', 'inputs': owned, 'protocol': protocol,
        'registration_hash': registration, 'shared_context_hash': shared, 'reports': analyses,
        'comparison': {'original_report_id': analyses[0]['report_id'], 'repaired_report_id': analyses[1]['report_id'],
            'same_frozen_task_corpus_rubric': True,
            'support_rate_change_on_registered_atoms': analyses[1]['controls']['clause']['full_inventory_support']['rate']
                - analyses[0]['controls']['clause']['full_inventory_support']['rate']},
        'deployment_authorized': False, 'evidence_kind': 'executed_format_bound_extraction_with_authored_semantics',
        'limitations': 'Complete reports provide context, but recovery metrics apply only to registered Finding atoms. '
            'Narrative prose and synthesis reviews are not automatically discovered or semantically judged. '
            'Original and repaired outputs are authored, not generated by models. Extraction executes on text alone; '
            'support, contradiction, unknown, question coverage and synthesis labels are supplied evidence, not NLP '
            'understanding. No population inference or deployment authority. Hashes establish local bindings, not '
            'authenticated sources, human independence or historical execution.'}
    return {**result, 'report_hash': canonical_hash(result)}


def replay_study(report):
    _require(isinstance(report, dict) and 'inputs' in report, 'retained complete inputs required')
    expected = run_study(report['inputs'])
    _require(canonical_hash(report) == canonical_hash(expected), 'retained analysis differs from complete re-execution')
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
