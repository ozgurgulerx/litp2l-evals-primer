"""Consistency tests for the book's machine-readable synthetic examples."""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPOSITORY_ROOT / "evals/cx-support/examples"


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES_ROOT / name).read_text(encoding="utf-8"))


class SyntheticBookExampleTests(unittest.TestCase):
    def test_human_annotation_example_has_overlap_and_adjudication(self) -> None:
        artifact = load_example("human-annotations-v1.json")
        case_ids = {item["case_id"] for item in artifact["items"]}
        label_counts = {
            case_id: sum(
                annotation["case_id"] == case_id
                for annotation in artifact["annotations"]
            )
            for case_id in case_ids
        }

        self.assertEqual(len(case_ids), 8)
        self.assertTrue(all(count >= 2 for count in label_counts.values()))
        self.assertGreaterEqual(len(artifact["adjudications"]), 1)

    def test_judge_calibration_counts_are_consistent(self) -> None:
        artifact = load_example("judge-calibration-v1.json")
        confusion = artifact["confusion_counts"]
        total = sum(confusion.values())
        false_pass_rate = confusion["judge_pass_human_fail"] / (
            confusion["judge_pass_human_fail"]
            + confusion["judge_fail_human_fail"]
        )

        self.assertEqual(total, artifact["sample_size"])
        self.assertEqual(total, 120)
        self.assertAlmostEqual(false_pass_rate, artifact["false_pass_rate"], places=6)
        self.assertEqual(artifact["authority_decision"]["tr"], "shadow_only")

    def test_dataset_change_preserves_lineage_and_role(self) -> None:
        artifact = load_example("dataset-change-v1.1.json")

        self.assertEqual(artifact["from_version"], "refund-v1.0")
        self.assertEqual(artifact["to_version"], "refund-v1.1")
        self.assertEqual(artifact["added_cases"][0]["dataset_role"], "regression")
        self.assertTrue(artifact["added_cases"][0]["source_incident_id"])
        self.assertTrue(artifact["review"]["approved"])

    def test_rag_claim_artifact_separates_correctness_and_support(self) -> None:
        artifact = load_example("rag-claims-v1.json")
        claims = artifact["claims"]
        chapter = (REPOSITORY_ROOT / "docs/rag-research-evals.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual(len(claims), 3)
        self.assertTrue(any(item["correct"] is False for item in claims))
        self.assertTrue(any(item["correct"] is None for item in claims))
        self.assertTrue(any(item["supported"] for item in claims))
        self.assertEqual(
            artifact["summary"],
            {
                "supported": sum(item["supported"] for item in claims),
                "contradicted": sum(
                    item["verdict"] == "contradicted" for item in claims
                ),
                "unsupported": sum(
                    item["verdict"].startswith("unsupported") for item in claims
                ),
                "truth_not_verified": sum(
                    item["correct"] is None for item in claims
                ),
            },
        )
        for claim in claims:
            with self.subTest(claim=claim["claim"]):
                self.assertIn(claim["claim"], chapter)

    def test_probability_calibration_artifact_recomputes_every_summary(self) -> None:
        artifact = load_example("probability-calibration-v1.json")
        predictions = artifact["predictions"]
        brier = sum(
            (item["confidence"] - item["correct"]) ** 2 for item in predictions
        ) / len(predictions)
        nll = -sum(
            item["correct"] * math.log(item["confidence"])
            + (1 - item["correct"]) * math.log(1 - item["confidence"])
            for item in predictions
        ) / len(predictions)
        ece = 0.0
        for bin_summary in artifact["reliability_bins"]:
            members = [
                item
                for item in predictions
                if item["confidence"] >= bin_summary["lower"]
                and (
                    item["confidence"] < bin_summary["upper"]
                    or (
                        bin_summary["upper_inclusive"]
                        and item["confidence"] == bin_summary["upper"]
                    )
                )
            ]
            mean_confidence = sum(item["confidence"] for item in members) / len(
                members
            )
            empirical_accuracy = sum(item["correct"] for item in members) / len(
                members
            )
            with self.subTest(reliability_bin=bin_summary["range"]):
                self.assertEqual(bin_summary["support"], len(members))
                self.assertAlmostEqual(
                    bin_summary["mean_confidence"], mean_confidence, places=6
                )
                self.assertAlmostEqual(
                    bin_summary["empirical_accuracy"], empirical_accuracy, places=6
                )
            ece += len(members) / len(predictions) * abs(
                mean_confidence - empirical_accuracy
            )

        self.assertEqual(len(predictions), 10)
        self.assertAlmostEqual(brier, artifact["scores"]["brier"], places=6)
        self.assertAlmostEqual(nll, artifact["scores"]["negative_log_likelihood"], places=6)
        self.assertAlmostEqual(ece, artifact["scores"]["ece"], places=6)
        self.assertEqual(
            [item["threshold"] for item in artifact["selective_thresholds"]],
            [0.6, 0.8, 0.9],
        )
        for summary in artifact["selective_thresholds"]:
            automated = [
                item
                for item in predictions
                if item["confidence"] >= summary["threshold"]
            ]
            wrong = sum(not item["correct"] for item in automated)
            with self.subTest(threshold=summary["threshold"]):
                self.assertEqual(summary["automated"], len(automated))
                self.assertEqual(summary["wrong"], wrong)
                self.assertAlmostEqual(
                    summary["coverage"], len(automated) / len(predictions), places=6
                )
                self.assertAlmostEqual(
                    summary["selective_risk"], wrong / len(automated), places=6
                )

    def test_production_canary_rolls_back_on_hard_invariant(self) -> None:
        artifact = load_example("production-canary-v1.json")

        self.assertEqual(artifact["candidate"]["duplicate_refunds"], 1)
        self.assertEqual(artifact["decision"]["action"], "rollback")
        self.assertIn("hard:duplicate_refund", artifact["decision"]["reasons"])


if __name__ == "__main__":
    unittest.main()
