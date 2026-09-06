"""Frozen invented report/corpus: executable joins plus explicitly authored semantic review."""

import argparse
import json
import re
from datetime import date
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(value, keys):
    _require(isinstance(value, dict) and set(value) == set(keys), 'exact registered fields required')


def _id(value):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value), 'opaque identifier required')


def _date(value):
    _require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'ISO date required')
    return date.fromisoformat(value)


def _text(value):
    _require(isinstance(value, str) and 0 < len(value) <= 10000, 'bounded nonempty text required')


def _span(text, quote):
    start = text.index(quote)
    return {'start': start, 'end': start + len(quote), 'quote': quote}


def _check_span(text, span):
    _fields(span, ('start', 'end', 'quote'))
    for value in (span['start'], span['end']):
        kind = type(value)
        _require(kind is int, 'span boundaries must be exact integers')
    _require(0 <= span['start'] < span['end'] <= len(text) and text[span['start']:span['end']] == span['quote'], 'span quote mismatch')


def _unique(rows, key):
    _require(isinstance(rows, list) and len(rows) <= 30, 'bounded record list required')
    for row in rows:
        _require(isinstance(row, dict) and key in row, 'record identity required')
        _id(row[key])
    result = {r[key]: r for r in rows}
    _require(len(result) == len(rows), 'duplicate registered ID')
    return result


def _current(source, as_of):
    target = _date(as_of)
    return _date(source['published_at']) <= target and _date(source['effective_from']) <= target and (
        source['effective_until'] is None or target < _date(source['effective_until']))


def _link_binding(claim, citation, sources):
    return canonical_hash({'claim': claim, 'citation': citation, 'source': sources.get(citation['source_id'])})


def example_inputs():
    sentences = ['The return window is 30 days.', 'Refunds settle within 5 business days.',
                 'Opened items are always refundable.', 'Return shipping is free.', 'The policy covers Northport purchases.']
    section_texts = [('returns', 'Returns', sentences[0] + ' [L1] ' + sentences[2] + ' [L3]'),
                     ('timing', 'Refund timing', sentences[1] + ' [L2]'),
                     ('shipping', 'Shipping', sentences[3] + ' [L4]'), ('scope', 'Scope', sentences[4])]
    body = '# Northport parcel-policy brief\n\nAs-of: 2026-09-07. Invented classroom report.\n\n'
    sections = []
    for key, heading, paragraph in section_texts:
        section = f'## {heading}\n{paragraph}\n\n'
        body += section
        sections.append({'section_id': key, 'span': _span(body, section)})
    scope = 'northport-consumer-returns'
    report = {'report_id': 'brief-v1', 'as_of': '2026-09-07', 'scope': scope, 'text': body, 'sections': sections}
    source_specs = [('policy-old', '2026-08-01', '2026-09-01', 'The return window is 30 days.'),
        ('policy-current', '2026-09-01', None, 'The return window is 14 days. Opened items are not refundable. The policy covers Northport purchases.'),
        ('payments', '2026-08-01', None, sentences[1]), ('shipping', '2026-08-01', None, sentences[3])]
    sources = [{'source_id': name, 'authority': 'invented-policy-owner', 'scope': scope, 'published_at': start,
                'effective_from': start, 'effective_until': end, 'text': text} for name, start, end, text in source_specs]
    lookup = {s['source_id']: s for s in sources}
    questions = [{'question_id': q, 'text': text} for q, text in (
        ('returns', 'What return window and opened-item rule apply?'), ('timing', 'How long does settlement take?'),
        ('shipping', 'Who pays return shipping?'), ('scope', 'Where does the policy apply?'), ('warranty', 'What warranty period applies?'))]
    question_ids = ('returns', 'timing', 'returns', 'shipping', 'scope')
    claims = [{'claim_id': f'C{i + 1}', 'question_id': q, 'section_id': q, 'span': _span(body, text)}
              for i, (q, text) in enumerate(zip(question_ids, sentences, strict=True))]
    citations = []
    for i, claim_id, source_id in ((1, 'C1', 'policy-old'), (2, 'C2', 'payments'), (3, 'C3', 'payments'), (4, 'C4', None)):
        citations.append({'citation_id': f'L{i}', 'claim_id': claim_id, 'source_id': source_id,
            'locator_span': _span(body, f'[L{i}]'),
            'source_span': _span(lookup[source_id]['text'], lookup[source_id]['text']) if source_id else None})
    adjudications = [{'citation_id': c['citation_id'], 'entailed': c['citation_id'] in ('L1', 'L2') if c['source_id'] else None,
        'reason': 'Authored sentence-level relation; not inferred by code.',
        'binding_hash': _link_binding(claims[int(c['claim_id'][1:]) - 1], c, lookup)} for c in citations]
    base = {'report': report, 'sources': sources, 'required_questions': questions, 'claims': claims,
            'citations': citations, 'link_adjudications': adjudications}
    refs = []
    for version in (0, 1):
        evidence = [('policy-old', sentences[0]) if version == 0 else ('policy-current', 'The return window is 14 days.'),
                    ('payments', sentences[1]), ('policy-current', 'Opened items are not refundable.'),
                    ('shipping', sentences[3]), ('policy-current', sentences[4])]
        reference = {'reference_id': f'reference-v{version + 1}', 'authority': 'authored-review-panel', 'scope': scope,
            'as_of': report['as_of'], 'reviewed_on': '2026-09-07' if version == 0 else '2026-09-08',
            'mode': 'historical-unqualified' if version == 0 else 'dated-reviewed', 'context_hash': canonical_hash(base),
            'supersedes_hash': None if version == 0 else canonical_hash(refs[0]),
            'judgments': [{'claim_id': f'C{i + 1}', 'correct': i != 2 and not (version == 1 and i == 0),
                'source_id': sid, 'source_span': _span(lookup[sid]['text'], quote),
                'claim_binding_hash': canonical_hash(claims[i]),
                'reason': 'Authored truth adjudication against this source for the fixed report date.'}
                for i, (sid, quote) in enumerate(evidence)]}
        refs.append(reference)
    return {**base, 'references': refs}


def _validate(inputs):
    _fields(inputs, ('report', 'sources', 'required_questions', 'claims', 'citations', 'link_adjudications', 'references'))
    report = inputs['report']
    _fields(report, ('report_id', 'as_of', 'scope', 'text', 'sections'))
    _id(report['report_id'])
    _id(report['scope'])
    _date(report['as_of'])
    _text(report['text'])
    sections = _unique(report['sections'], 'section_id')
    for section in sections.values():
        _fields(section, ('section_id', 'span'))
        _check_span(report['text'], section['span'])
    sources = _unique(inputs['sources'], 'source_id')
    _require(bool(sources), 'source corpus required')
    for source in sources.values():
        _fields(source, ('source_id', 'authority', 'scope', 'published_at', 'effective_from', 'effective_until', 'text'))
        _text(source['text'])
        _require(source['authority'] == 'invented-policy-owner' and source['scope'] == report['scope'], 'source authority/scope mismatch')
        _require(_date(source['published_at']) <= _date(source['effective_from']), 'publication after stated effectivity')
        if source['effective_until'] is not None:
            _require(_date(source['effective_from']) < _date(source['effective_until']), 'invalid effective interval')
    questions = _unique(inputs['required_questions'], 'question_id')
    _require(bool(questions), 'required questions cannot disappear')
    for question in questions.values():
        _fields(question, ('question_id', 'text'))
        _text(question['text'])
    claims = _unique(inputs['claims'], 'claim_id')
    _require(bool(claims), 'registered atomic claims required')
    for claim in claims.values():
        _fields(claim, ('claim_id', 'question_id', 'section_id', 'span'))
        _require(claim['question_id'] in questions and claim['section_id'] in sections, 'claim/question/section join mismatch')
        _check_span(report['text'], claim['span'])
        section_span = sections[claim['section_id']]['span']
        _require(section_span['start'] <= claim['span']['start'] < claim['span']['end'] <= section_span['end'], 'claim outside section')
    citations = _unique(inputs['citations'], 'citation_id')
    for citation in citations.values():
        _fields(citation, ('citation_id', 'claim_id', 'source_id', 'locator_span', 'source_span'))
        _require(citation['claim_id'] in claims, 'foreign citation claim')
        _check_span(report['text'], citation['locator_span'])
        _require(citation['locator_span']['quote'] == f"[{citation['citation_id']}]", 'citation marker mismatch')
        if citation['source_id'] is None:
            _require(citation['source_span'] is None, 'explicit unresolved link cannot contain source span')
        else:
            _require(citation['source_id'] in sources, 'foreign source ID; unresolved links must be explicit None')
            _check_span(sources[citation['source_id']]['text'], citation['source_span'])
    adjudications = _unique(inputs['link_adjudications'], 'citation_id')
    _require(set(adjudications) == set(citations), 'every attempted link needs an explicit authored adjudication')
    for key, row in adjudications.items():
        _fields(row, ('citation_id', 'entailed', 'reason', 'binding_hash'))
        _text(row['reason'])
        citation = citations[key]
        _require(isinstance(row['entailed'], bool) if citation['source_id'] is not None else row['entailed'] is None, 'invalid entailment judgment')
        _require(row['binding_hash'] == _link_binding(claims[citation['claim_id']], citation, sources), 'semantic adjudication binding mismatch')
    context = canonical_hash({k: v for k, v in inputs.items() if k != 'references'})
    refs = inputs['references']
    _require(isinstance(refs, list) and len(refs) == 2, 'original and corrected reference snapshots required')
    for i, ref in enumerate(refs):
        _fields(ref, ('reference_id', 'authority', 'scope', 'as_of', 'reviewed_on', 'mode', 'context_hash', 'supersedes_hash', 'judgments'))
        _id(ref['reference_id'])
        _require(ref['authority'] == 'authored-review-panel' and ref['scope'] == report['scope'] and ref['as_of'] == report['as_of'], 'reference authority/scope/date mismatch')
        _require(_date(ref['reviewed_on']) >= _date(ref['as_of']) and ref['context_hash'] == context, 'reference date/context mismatch')
        _require(ref['mode'] == ('historical-unqualified' if i == 0 else 'dated-reviewed'), 'reference assessment mode mismatch')
        _require(ref['supersedes_hash'] == (None if i == 0 else canonical_hash(refs[0])), 'reference correction chain mismatch')
        judgments = _unique(ref['judgments'], 'claim_id')
        _require(set(judgments) == set(claims), 'complete reference judgments required')
        for key, judgment in judgments.items():
            _fields(judgment, ('claim_id', 'correct', 'source_id', 'source_span', 'claim_binding_hash', 'reason'))
            _require(isinstance(judgment['correct'], bool) and judgment['source_id'] in sources, 'invalid truth review')
            _text(judgment['reason'])
            _check_span(sources[judgment['source_id']]['text'], judgment['source_span'])
            _require(judgment['claim_binding_hash'] == canonical_hash(claims[key]), 'truth claim binding mismatch')
            if i == 1:
                _require(_current(sources[judgment['source_id']], ref['as_of']), 'corrected reference requires dated in-scope evidence')
    _require(refs[0]['reference_id'] != refs[1]['reference_id'] and _date(refs[1]['reviewed_on']) > _date(refs[0]['reviewed_on']), 'new dated reference identity required')
    return claims, citations, sources, adjudications, context


def _ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator, 'rate': numerator / denominator if denominator else None}


def _citation_analysis(inputs, claims, citations, sources, adjudications):
    links = [{'citation_id': key, 'claim_id': row['claim_id'], 'source_id': row['source_id'],
        'resolved': row['source_id'] is not None, 'entailed': adjudications[key]['entailed'],
        'current': _current(sources[row['source_id']], inputs['report']['as_of']) if row['source_id'] is not None else None,
        'adjudication_hash': canonical_hash(adjudications[key])} for key, row in citations.items()]
    resolved = [r for r in links if r['resolved']]
    supported = [r for r in links if r['entailed'] is True]
    return {'links': links, 'unique_resolved_source_count': len({r['source_id'] for r in resolved}),
        'metrics': {'resolved_links': _ratio(len(resolved), len(links)),
            'entailed_all_attempted_links': _ratio(len(supported), len(links)),
            'entailed_resolved_links': _ratio(len(supported), len(resolved)),
            'claims_with_resolved_citation': _ratio(len({r['claim_id'] for r in resolved}), len(claims)),
            'claims_supported_by_citations': _ratio(len({r['claim_id'] for r in supported}), len(claims)),
            'claims_supported_by_current_citations': _ratio(len({r['claim_id'] for r in supported if r['current']}), len(claims))}}


def _grade(inputs, reference, analysis, context):
    judgments = {r['claim_id']: r for r in reference['judgments']}
    claims = [{'claim_id': c['claim_id'], 'question_id': c['question_id'], 'correct': judgments[c['claim_id']]['correct'],
        'citation_supported': any(r['claim_id'] == c['claim_id'] and r['entailed'] is True for r in analysis['links'])}
        for c in inputs['claims']]
    questions = []
    for question in inputs['required_questions']:
        mapped = [c for c in claims if c['question_id'] == question['question_id']]
        questions.append({'question_id': question['question_id'], 'claim_ids': [c['claim_id'] for c in mapped],
            'status': 'omitted' if not mapped else 'correctly_answered' if all(c['correct'] for c in mapped) else 'addressed_incorrectly'})
    grade = {'reference': reference, 'reference_hash': canonical_hash(reference), 'context_hash': context,
        'claims': claims, 'factual_correctness': _ratio(sum(c['correct'] for c in claims), len(claims)),
        'required_questions': {'rows': questions, 'addressed': _ratio(sum(q['status'] != 'omitted' for q in questions), len(questions)),
            'correctly_answered': _ratio(sum(q['status'] == 'correctly_answered' for q in questions), len(questions)),
            'justified_abstention': _ratio(0, len(questions))}}
    return {**grade, 'grade_hash': canonical_hash(grade)}


def run_study(inputs=None):
    owned = json.loads(json.dumps(example_inputs() if inputs is None else inputs, allow_nan=False))
    claims, citations, sources, adjudications, context = _validate(owned)
    analysis = _citation_analysis(owned, claims, citations, sources, adjudications)
    original, updated = [_grade(owned, ref, analysis, context) for ref in owned['references']]
    correction = {'previous_reference_hash': original['reference_hash'], 'updated_reference_hash': updated['reference_hash'],
        'original_grade_hash': original['grade_hash'], 'reassessed_grade_hash': updated['grade_hash'],
        'changed_claim_ids': [a['claim_id'] for a, b in zip(original['claims'], updated['claims'], strict=True) if a['correct'] != b['correct']],
        'reviewed_on': owned['references'][1]['reviewed_on'],
        'review_note': 'Authored correction exposes a false pass in the old reference; the report and corpus did not change.'}
    protocol = {'span_unit': 'Python Unicode code-point offsets; end exclusive', 'material_claims': 'supplied atomic claim inventory, not extraction',
        'semantic_annotations': 'authored source-span entailment, question mapping and truth judgments, not automatic understanding',
        'dates': 'as_of and source effective intervals govern current support; review date records later correction',
        'abstention': 'no registered claim is an abstention; omitted questions are not justified abstentions'}
    report = {'schema': 'report-citations-v1', 'inputs': owned, 'protocol': protocol,
        'registration_hash': canonical_hash({'inputs': owned, 'protocol': protocol}),
        'citation_analysis': analysis, 'original_grade': original, 'reassessed_grade': updated, 'correction': correction,
        'deployment_authorized': False, 'evidence_kind': 'synthetic_authored_report_analysis',
        'limitations': 'Entire corpus, report and reviews are invented. Computation verifies spans, bindings, dates '
            'and aggregates supplied semantic judgments; it does not discover entailment, factual truth or all '
            'material claims. Required-question completeness is relative to the registered authored mapping. '
            'No actual long-report/model performance, human review or deployment qualification is established. '
            'The historical reference is deliberately wrong for one claim. Reassessment changes the instrument, '
            'not the report. Hashes preserve local consistency, not authenticated authority or execution history.'}
    return {**report, 'report_hash': canonical_hash(report)}


def replay_study(report):
    _require(isinstance(report, dict) and 'inputs' in report, 'retained inputs required')
    expected = run_study(report['inputs'])
    _require(canonical_hash(report) == canonical_hash(expected), 'retained report differs from reanalysis')
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
