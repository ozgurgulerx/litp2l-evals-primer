"""End-to-end tests for the local CX eval command-line workflow."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab.__main__ import main


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class CxEvalCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (sys.executable, "-m", "cx_eval_lab", *arguments),
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_reference_demo_writes_an_auditable_passing_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "reference-report.json"

            result = self.run_cli(
                "eval",
                "--agent",
                "reference",
                "--output",
                str(output_path),
            )
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("lab_pass", report["decision"]["action"])
        self.assertEqual(5, report["evaluation"]["case_count"])
        self.assertEqual("refund-v1", report["evaluation"]["dataset_version"])
        self.assertIn("lab_pass", result.stdout)

    def test_broken_agent_returns_a_blocking_exit_code_and_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "failed-report.json"

            result = self.run_cli(
                "eval",
                "--agent",
                "blind-retry",
                "--output",
                str(output_path),
            )
            report = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(2, result.returncode)
        self.assertEqual("block", report["decision"]["action"])
        self.assertTrue(report["decision"]["failed_rules"])

    def test_cli_entrypoint_returns_success_for_the_reference_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "direct-report.json"
            arguments = [
                "cx_eval_lab",
                "eval",
                "--agent",
                "reference",
                "--output",
                str(output_path),
            ]

            with patch.object(sys, "argv", arguments):
                exit_code = main()

        self.assertEqual(0, exit_code)

    def test_paired_experiment_writes_raw_trials_comparison_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "paired-experiment.json"

            result = self.run_cli(
                "experiment",
                "--baseline-agent",
                "reference",
                "--candidate-agent",
                "reference",
                "--minimum-independent-clusters",
                "5",
                "--output",
                str(output_path),
            )
            artifact = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("lab_pass", artifact["receipt"]["action"])
        self.assertEqual("lab_only", artifact["receipt"]["authority_ceiling"])
        self.assertEqual(10, len(artifact["experiment"]["baseline_trials"]))
        self.assertEqual(10, len(artifact["experiment"]["candidate_trials"]))
        self.assertEqual("pass", artifact["comparison"]["status"])
        self.assertIn("manifest_hash", artifact["experiment"])
        self.assertIn("raw_artifact_hash", artifact["receipt"])

    def test_paired_experiment_holds_when_independent_evidence_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "paired-hold.json"

            result = self.run_cli(
                "experiment",
                "--baseline-agent",
                "reference",
                "--candidate-agent",
                "reference",
                "--minimum-independent-clusters",
                "30",
                "--output",
                str(output_path),
            )
            artifact = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(3, result.returncode, result.stderr)
        self.assertEqual("hold", artifact["receipt"]["action"])
        self.assertEqual("inconclusive", artifact["comparison"]["status"])


if __name__ == "__main__":
    unittest.main()
