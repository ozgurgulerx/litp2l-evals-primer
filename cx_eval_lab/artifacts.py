"""Portable execution evidence and offline deterministic re-grading.

Hashes detect changed content relative to a retained digest. They are not
signatures, an attestation of execution, or permission to deploy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from cx_eval_lab.evaluators import evaluate_case
from cx_eval_lab.models import (
    AgentOutput, RefundCase, RuntimeEvidence, SemanticEvaluationReceipt,
    ToolEvent, WorldSnapshot,
)


@dataclass(frozen=True)
class TrialArtifact:
    """Store canonical JSON rather than a mutable nested payload."""

    payload_json: str

    @classmethod
    def capture(cls, payload: dict) -> TrialArtifact:
        return cls(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":"), allow_nan=False))

    @property
    def content_hash(self) -> str:
        from cx_eval_lab.evidence import canonical_hash
        return canonical_hash(json.loads(self.payload_json))

    def to_dict(self) -> dict:
        return {"artifact_hash": self.content_hash,
                "payload": json.loads(self.payload_json)}


def _regrade(payload, trusted_calibration_hashes):
    if payload['schema'] in {'resolution-trial-v1', 'resolution-trial-v2'}:
        from cx_eval_lab.resolution_evidence import regrade
        return regrade(payload, trusted_calibration_hashes)
    if payload["schema"] != "refund-trial-v1":
        raise ValueError("unsupported trial artifact schema")
    case = RefundCase.from_dict(payload["case"])
    output_data = payload["output"]
    runtime = output_data.get("runtime_evidence")
    if runtime is not None:
        runtime = RuntimeEvidence(**{**runtime, "response_ids": tuple(runtime["response_ids"])})
    output = AgentOutput(**{**output_data, "runtime_evidence": runtime})
    events = tuple(ToolEvent(**{**event, "details": tuple(event["details"].items())})
                   for event in payload["events"])
    state = WorldSnapshot(**{
        **payload["final_state"],
        "refund_idempotency_keys": tuple(payload["final_state"]["refund_idempotency_keys"]),
    })
    receipt_data = payload["semantic_evaluation_receipt"]
    receipt = None if receipt_data is None else SemanticEvaluationReceipt(**receipt_data)
    registered = frozenset(payload["qualified_semantic_calibration_hashes"])
    if not registered.issubset(trusted_calibration_hashes):
        raise ValueError("replay requires independently trusted calibration hashes")
    result = evaluate_case(
        case, output, events, state, latency_ms=payload["latency_ms"],
        cost_usd=payload["cost_usd"], execution_error=payload["execution_error"],
        semantic_evaluation_receipt=receipt,
        qualified_semantic_calibration_hashes=registered,
        policy_version=payload["policy_version"],
    )
    if payload.get("semantic_stage") is not None:
        return replace(result, semantic_stage_json=json.dumps(payload["semantic_stage"], sort_keys=True))
    return result


def replay_packet(packet: dict, *, trusted_calibration_hashes=frozenset()):
    """Validate and re-grade a complete packet with the installed grader.

This is exact replay validation, not silent migration to a new grader. Keep
the original packet and use its pinned code revision if grading has changed.
Calibration authority comes from the caller, never from the packet itself.
"""
    try:
        return _replay_packet(packet, trusted_calibration_hashes)
    except (KeyError, TypeError) as error:
        raise ValueError("malformed trial artifact packet") from error


def _replay_packet(packet, trusted_calibration_hashes):
    from cx_eval_lab.evidence import ExperimentManifest, canonical_hash
    manifest = ExperimentManifest(**packet["manifest"])
    if manifest.content_hash != packet["manifest_hash"]:
        raise ValueError("manifest hash mismatch")
    if any(a['payload']['schema'] in {'resolution-trial-v1', 'resolution-trial-v2'}
           for a in packet['trial_artifacts']):
        from cx_eval_lab.resolution_evidence import validate_packet
        validate_packet(packet, manifest)
    artifacts = {}
    for artifact in packet["trial_artifacts"]:
        digest = artifact["artifact_hash"]
        if canonical_hash(artifact["payload"]) != digest:
            raise ValueError("artifact hash mismatch")
        if digest in artifacts:
            raise ValueError("duplicate artifact hash")
        artifacts[digest] = artifact["payload"]
    results, used, keys = [], set(), set()
    for arm in ("baseline", "candidate"):
        for row in packet[f"{arm}_trials"]:
            key = (arm, row["case_id"], row["trial_index"])
            if key in keys or row["arm"] != arm:
                raise ValueError("duplicate or incorrect trial identity")
            keys.add(key)
            if row["manifest_hash"] != manifest.content_hash:
                raise ValueError("trial manifest hash mismatch")
            digest = row["artifact_hash"]
            if digest not in artifacts or digest in used:
                raise ValueError("missing or reused trial artifact")
            used.add(digest)
            payload = artifacts[digest]
            identity = {name: row[name] for name in
                        ("case_id", "trial_index", "arm", "manifest_hash")}
            if payload["identity"] != identity or payload["case"]["case_id"] != row["case_id"]:
                raise ValueError("artifact identity mismatch")
            result = _regrade(payload, trusted_calibration_hashes)
            if canonical_hash(result.to_dict()) != canonical_hash(payload["evaluation"]):
                raise ValueError("replayed grade differs from retained evaluation")
            expected = {
                "passed": result.passed, "latency_ms": result.latency_ms,
                "cost_usd": result.cost_usd,
                "cluster_id": _population_entry(payload)[1],
                "failed_checks": [check.name for check in result.checks if not check.passed],
            }
            if any(row[name] != value for name, value in expected.items()):
                raise ValueError("trial summary differs from replayed evidence")
            results.append(result)
    if not keys or used != set(artifacts):
        raise ValueError("empty packet or unreferenced artifact")
    case_ids = {case_id for _, case_id, _ in keys}
    expected_keys = {(arm, case_id, index) for arm in ("baseline", "candidate")
                     for case_id in case_ids for index in range(manifest.repetitions)}
    if keys != expected_keys:
        raise ValueError("incomplete registered repetitions or paired arms")
    population = [artifacts[row["artifact_hash"]]
                  for row in packet["baseline_trials"] if row["trial_index"] == 0]
    population_digest = canonical_hash(
        [_population_entry(payload) for payload in population]
    )
    if population_digest != manifest.population_hash:
        raise ValueError("registered population hash mismatch")
    return tuple(results)


def _population_entry(payload):
    if payload['schema'] in {'resolution-trial-v1', 'resolution-trial-v2'}:
        from cx_eval_lab.resolution_evidence import case_from_dict, population_entry
        return population_entry(case_from_dict(payload['case']))
    case = payload['case']
    return [case['case_id'], case['customer_id'], case['slices']]
