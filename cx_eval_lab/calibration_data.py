"""Compile scoped calibration records from retained reviewed annotation rows.

Reviewer allowlists and excluded split inventories are trusted operator inputs.
This validates their consistency, not human identity or annotation authenticity.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.semantic import CalibrationRecord


POLICY_FIELDS = {'issued_at', 'expires_at', 'minimum_per_class',
                 'max_false_pass_upper', 'max_false_block_upper', 'max_abstention_rate'}
ROW_FIELDS = {'id', 'group_id', 'split', 'scope', 'evidence', 'reviews',
              'adjudication', 'judgment'}
JUDGE_FIELDS = {'verdict', 'evaluator_version', 'configuration_hash',
                'criterion_id', 'evidence_hash'}
LABELS = {'truthful', 'false'}


def _fields(value, expected, name):
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f'{name} requires exactly the registered schema fields')


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} requires nonempty text')
    return value


def _identifiers(values, name):
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple, set, frozenset)):
        raise ValueError(f'{name} must be an explicit identifier collection')
    return frozenset(_text(value, name) for value in values)


def _reviewed_label(row, trusted_reviewers):
    reviews = row['reviews']
    if not isinstance(reviews, list) or len(reviews) != 2:
        raise ValueError('exactly two independent reviews are required')
    for review in reviews:
        _fields(review, {'reviewer_id', 'label'}, 'review')
        if (review['reviewer_id'] not in trusted_reviewers
                or review['label'] not in LABELS):
            raise ValueError('review must have an allowed reviewer and resolved label')
    reviewers = {review['reviewer_id'] for review in reviews}
    if len(reviewers) != 2:
        raise ValueError('reviews must have different reviewer identities')
    adjudication = row['adjudication']
    if reviews[0]['label'] == reviews[1]['label']:
        if adjudication is not None:
            raise ValueError('agreement cannot be silently overridden by adjudication')
        return reviews[0]['label']
    _fields(adjudication, {'reviewer_id', 'label', 'reason'}, 'adjudication')
    if (adjudication['reviewer_id'] not in trusted_reviewers
            or adjudication['reviewer_id'] in reviewers or adjudication['label'] not in LABELS):
        raise ValueError('adjudication requires a third allowed reviewer and resolved label')
    _text(adjudication['reason'], 'adjudication reason')
    return adjudication['label']


def _validated_rows(data, trusted_reviewers, excluded_groups, excluded_hashes):
    rows = data['rows']
    if not isinstance(rows, list) or not 2 <= len(rows) <= 1000:
        raise ValueError('calibration requires 2 to 1000 rows')
    identities, groups, hashes = set(), set(), set()
    results = []
    config = None
    for row in rows:
        _fields(row, ROW_FIELDS, 'annotation row')
        identity, group = _text(row['id'], 'id'), _text(row['group_id'], 'group_id')
        if row['split'] != 'calibration' or row['scope'] != data['scope']:
            raise ValueError('row must belong to the registered calibration split and scope')
        if not isinstance(row['evidence'], dict) or not row['evidence']:
            raise ValueError('retained nonempty evidence is required')
        digest = canonical_hash(row['evidence'])
        if (identity in identities or group in groups or digest in hashes
                or group in excluded_groups or digest in excluded_hashes):
            raise ValueError('duplicate or excluded split evidence cannot enter calibration')
        judgment = row['judgment']
        _fields(judgment, JUDGE_FIELDS, 'judgment')
        if judgment['verdict'] not in {'pass', 'fail', 'abstain'}:
            raise ValueError('invalid judge verdict')
        if judgment['evidence_hash'] != digest:
            raise ValueError('judge evidence binding mismatch')
        row_config = tuple(_text(judgment[key], key) for key in
                           ('evaluator_version', 'configuration_hash', 'criterion_id'))
        if config is not None and config != row_config:
            raise ValueError('mixed evaluator configurations cannot share qualification')
        config = row_config
        results.append((_reviewed_label(row, trusted_reviewers), judgment['verdict']))
        identities.add(identity)
        groups.add(group)
        hashes.add(digest)
    return config, tuple(results)


def compile_calibration(annotations, *, policy, trusted_reviewers,
                        excluded_group_ids, excluded_evidence_hashes):
    """Derive counts; never accept caller-supplied counts or an authority upgrade."""
    # Own a JSON snapshot; neither mutate caller data nor accept NaN/opaque objects.
    try:
        data = json.loads(json.dumps(annotations, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise ValueError('annotations must be finite JSON data') from error
    _fields(data, {'schema_version', 'evidence_kind', 'scope', 'rows'}, 'annotations')
    if data['schema_version'] != 'calibration-annotations-v1':
        raise ValueError('unsupported annotation schema')
    _fields(policy, POLICY_FIELDS, 'qualification policy')
    _fields(data['scope'], {'dataset_version', 'policy_version', 'slices'}, 'scope')
    scope = data['scope']
    _text(scope['dataset_version'], 'dataset version')
    _text(scope['policy_version'], 'policy version')
    slices = _identifiers(scope['slices'], 'slices')
    if not slices or len(slices) != len(scope['slices']):
        raise ValueError('scope requires unique nonempty slice identifiers')
    config, outcomes = _validated_rows(
        data, _identifiers(trusted_reviewers, 'trusted reviewers'),
        _identifiers(excluded_group_ids, 'excluded groups'),
        _identifiers(excluded_evidence_hashes, 'excluded evidence hashes'))
    return CalibrationRecord(
        evaluator_version=config[0], configuration_hash=config[1], criterion_id=config[2],
        dataset_versions=(scope['dataset_version'],), policy_versions=(scope['policy_version'],),
        slice_scopes=(tuple(sorted(slices)),), evidence_kind=data['evidence_kind'],
        label_artifact_hash=canonical_hash(data),
        truthful_examples=sum(label == 'truthful' for label, _ in outcomes),
        false_examples=sum(label == 'false' for label, _ in outcomes),
        false_passes=sum(label == 'false' and verdict == 'pass' for label, verdict in outcomes),
        false_blocks=sum(label == 'truthful' and verdict != 'pass' for label, verdict in outcomes),
        abstentions=sum(verdict == 'abstain' for _, verdict in outcomes), **policy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        annotations = json.loads(args.input.read_text())
        config = json.loads(args.config.read_text())
        _fields(config, {'policy', 'trusted_reviewers', 'excluded_group_ids',
                         'excluded_evidence_hashes'}, 'operator config')
        record = compile_calibration(annotations, **config)
        report = {'annotations': annotations, 'operator_config': config,
                  'record': asdict(record), 'record_hash': record.content_hash,
                  'error_bounds': record.error_bounds, 'deployment_authorized': False,
                  'status': 'compiled_not_authenticated_or_deployment_qualified'}
        with args.output.open('x') as handle:
            handle.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    except (ValueError, TypeError, OSError) as error:
        parser.exit(2, f'Calibration compilation failed: {type(error).__name__}\n')


if __name__ == '__main__':
    main()
