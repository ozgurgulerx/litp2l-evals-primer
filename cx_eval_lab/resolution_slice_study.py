"""Retrospective synthetic native slices; replay is not a new agent experiment."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from cx_eval_lab.calibration_data import compile_calibration
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.resolution_slices import derive_resolution_slice_report


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _plan(packet):
    cases = {a['payload']['case']['case_id']: a['payload']['case'] for a in packet['trial_artifacts']}
    return {'schema': 'resolution-slice-plan-v1', 'required_slices': [], 'case_labels': {
        name: ['clarification:required' if case['required_clarifications'] else 'clarification:not-required',
               'resolution:unresolved' if case['expected_order_id'] is None else 'resolution:target-known']
        for name, case in sorted(cases.items())}}


def derive_study(source: Path, *, expected_source_sha256: str, trusted_calibration_hashes: frozenset):
    """Explicit caller anchors select a frozen synthetic artifact, not current authority."""
    raw = source.read_bytes()
    digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
    _require(digest == expected_source_sha256, 'source byte hash mismatch')
    try:
        data = json.loads(raw)
        # Reject non-finite values even in fields not used by the diagnostic.
        json.dumps(data, allow_nan=False)
        _require(data['study'] == 'native-resolution-semantic-study-v1'
                 and data['evidence_kind'] == 'executed_deterministic_mock'
                 and data['deployment_authorized'] is False, 'expected synthetic native study')
        calibration = data['calibration']
        _require(calibration['annotations']['evidence_kind'] == 'synthetic'
                 and calibration['deployment_authorized'] is False, 'expected synthetic calibration')
        record = compile_calibration(calibration['annotations'], **calibration['operator_config'])
        _require(canonical_hash(asdict(record)) == canonical_hash(calibration['record'])
                 and record.content_hash == calibration['record_hash'], 'compiled calibration mismatch')
        _require(isinstance(trusted_calibration_hashes, frozenset)
                 and trusted_calibration_hashes == frozenset({record.content_hash}),
                 'explicit caller trust must select this synthetic calibration hash')
        _require(isinstance(data['comparisons'], list) and len(data['comparisons']) == 3,
                 'expected three native comparisons')
        comparisons = []
        for original in data['comparisons']:
            packet = original['packet']
            _require(packet['manifest']['measurement_kind'] == 'synthetic'
                     and all(a['payload']['schema'] == 'resolution-trial-v2'
                             for a in packet['trial_artifacts']), 'expected synthetic native-v2 packet')
            plan = _plan(packet)
            report = derive_resolution_slice_report(packet, plan,
                trusted_calibration_hashes=trusted_calibration_hashes)
            comparisons.append({'candidate': original['candidate'], 'packet_hash': canonical_hash(packet),
                'original_release_receipt_hash': canonical_hash(original['release_receipt']),
                'original_release_action': original['release_receipt']['action'],
                'plan': plan, 'report': report})
        result = {'schema': 'resolution-slice-study-v1',
            'source': {'file': source.name, 'bytes_sha256': digest, 'canonical_hash': canonical_hash(data)},
            'calibration_hash': record.content_hash, 'comparisons': comparisons,
            'new_agent_executions': False, 'deployment_authorized': False,
            'evidence_kind': 'retrospective_replay_of_synthetic_native_packets',
            'limitations': 'Existing mock tool histories are replayed and regraded; no new agent or model '
                'executions, independent human labels, or current qualification. Source byte digest is '
                'distinct from canonical JSON hashes. Calibration compilation checks retained fixture '
                'consistency; caller-selected trust is pedagogical, not authenticated authority. Slice '
                'labels use full case preconditions retrospectively and remain exploratory, never a '
                'new release condition. Original packets and release receipts remain unchanged.'}
        return {**result, 'report_hash': canonical_hash(result)}
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError) as error:
        raise ValueError('malformed retained native study') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('docs/assets/native-resolution-semantic-v1.json'))
    parser.add_argument('--expected-source-sha256', required=True)
    parser.add_argument('--trusted-calibration-hash', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output path')
    result = derive_study(args.source, expected_source_sha256=args.expected_source_sha256,
                          trusted_calibration_hashes=frozenset(args.trusted_calibration_hash))
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
