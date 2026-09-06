"""Contract tests for the Evals Primer book scaffold."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import unquote
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CHAPTERS = (
    "docs/index.md",
    "docs/foundations.md",
    "docs/dataset-design.md",
    "docs/metrics.md",
    "docs/llm-as-a-judge.md",
    "docs/human-evaluation.md",
    "docs/robustness-safety.md",
    "docs/rag-research-evals.md",
    "docs/agent-evals.md",
    "docs/benchmark-reproducibility.md",
    "docs/production-evals.md",
    "docs/checklist.md",
    "docs/build-the-system.md",
    "docs/evidence-spine.md",
    "docs/cx-evidence-walkthrough.md",
    "docs/references.md",
    "docs/courses.md",
    "docs/interview-drills.md",
    "docs/source-coverage.md",
    "docs/system-studies.md",
    "docs/research-to-practice.md",
    "docs/long-running-serving.md",
    "docs/modern-agent-architectures.md",
    "docs/knowledge-action-study.md",
    "docs/cross-run-isolation-study.md",
    "docs/eval-operations-integrity.md",
)

DEPTH_CHAPTERS = {
    "docs/foundations.md": (
        "Canonical vocabulary",
        "Artifact: evaluation contract",
        "Failure modes",
        "Exercise",
    ),
    "docs/dataset-design.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "Dataset health",
    ),
    "docs/metrics.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "Inconclusive",
    ),
    "docs/llm-as-a-judge.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "risk–coverage",
    ),
    "docs/human-evaluation.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "adjudication",
    ),
    "docs/robustness-safety.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "false refusal",
    ),
    "docs/rag-research-evals.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "atomic claim",
    ),
    "docs/agent-evals.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "partial order",
        "Isolate the evaluator",
    ),
    "docs/benchmark-reproducibility.md": (
        "Worked example",
        "Failure mode",
        "Artifact",
        "Exercise",
        "construct validity",
        "evaluation integrity",
    ),
    "docs/production-evals.md": (
        "Deployment simulation",
        "Artifact: production sample",
        "Eval-system metrics",
        "Failure modes",
        "Exercise",
    ),
    "docs/checklist.md": (
        "Artifact: release manifest",
        "Exception",
        "Failure modes",
        "Exercise",
    ),
    "docs/system-studies.md": (
        "Worked comparison",
        "Portability",
        "Operational case patterns",
        "Dynamic behavioral evaluation",
        "Petri",
        "Bloom",
        "Exercise",
    ),
    "docs/research-to-practice.md": (
        "Evidence maturity rubric",
        "Deployment proof matrix",
        "What the evidence does not prove",
        "Worked example",
        "Artifact: practice-evidence ledger",
        "Exercise",
    ),
    "docs/evidence-spine.md": (
        "prerequisite graph",
        "Statistical non-inferiority",
        "Sample size and sequential looks",
        "Noisy labels and judge-error propagation",
        "Repeated holdout use",
        "Artifact: paired evidence receipt",
        "Exercise",
    ),
    "docs/long-running-serving.md": (
        "durable state",
        "Four-arm persistence experiment",
        "Human–agent collaboration outcomes",
        "Serving failures are behavioral interventions",
        "Evidence added in this chapter",
        "Exercise",
    ),
    "docs/modern-agent-architectures.md": (
        "Knowledge-to-action systems",
        "Skills and capability selection",
        "Voice and multimodal workflows",
        "Multi-agent evaluation",
        "Agent-family-specific evidence",
        "Evidence added in this chapter",
        "Exercise",
    ),
    "docs/eval-operations-integrity.md": (
        "Evaluation-service architecture",
        "Resumable runs",
        "Model-versus-harness factorial experiment",
        "Evaluation integrity is a runtime boundary",
        "Simulator qualification and deployment backtesting",
        "Evidence added in this chapter",
        "Exercise",
    ),
    "docs/interview-drills.md": (
        "Thirteen-theme drill map",
        "Answer contract",
        "Whiteboard drills",
        "Evidence receipts",
    ),
}


class BookConfigurationTests(unittest.TestCase):
    def test_configuration_uses_green_material_theme(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")

        self.assertRegex(configuration, r"(?m)^\s+name:\s+material\s*$")
        self.assertRegex(configuration, r"(?m)^\s+primary:\s+green\s*$")
        self.assertRegex(configuration, r"(?m)^\s+accent:\s+light green\s*$")

    def test_configuration_uses_custom_topic_favicon(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        favicon = REPOSITORY_ROOT / "docs/assets/favicon.svg"

        self.assertIn("favicon: assets/favicon.svg", configuration)
        self.assertTrue(favicon.is_file())
        self.assertIn("<svg", favicon.read_text(encoding="utf-8"))

    def test_navigation_references_every_chapter(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")

        for chapter in EXPECTED_CHAPTERS:
            relative_chapter = chapter.removeprefix("docs/")
            with self.subTest(chapter=relative_chapter):
                self.assertIn(relative_chapter, configuration)
                self.assertTrue((REPOSITORY_ROOT / chapter).is_file())

    def test_chapter_headings_are_integrated_into_left_navigation(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        judge_chapter = (REPOSITORY_ROOT / "docs/llm-as-a-judge.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("- toc.integrate", configuration)
        self.assertIn("- toc.follow", configuration)
        self.assertNotIn("- navigation.indexes", configuration)
        self.assertRegex(judge_chapter, r"(?m)^## Calibration$")

    def test_mathematics_uses_arithmatex_and_a_mathjax_runtime(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        mathjax_configuration = REPOSITORY_ROOT / "docs/javascripts/mathjax.js"

        self.assertIn("pymdownx.arithmatex", configuration)
        self.assertIn("javascripts/mathjax.js", configuration)
        self.assertIn("tex-mml-chtml.js", configuration)
        self.assertTrue(mathjax_configuration.is_file())
        self.assertIn("window.MathJax", mathjax_configuration.read_text(encoding="utf-8"))

    def test_structure_assigns_every_eval_family_to_an_explicit_home(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        chapter_contracts = {
            "docs/foundations.md": (
                "The control system: four planes",
                "The evaluation grid: three axes",
                "Step / component",
                "Trajectory",
                "Outcome",
            ),
            "docs/dataset-design.md": (
                "Sealed acceptance",
                "Label access",
                "executable specification",
            ),
            "docs/metrics.md": (
                "Worst value-weighted slice",
                "confidence interval",
                "pass@k",
                "pass^k",
                "runner",
            ),
            "docs/llm-as-a-judge.md": ("Frozen calibration set",),
            "docs/production-evals.md": ("Trace taxonomy", "WATCH", "LOCALIZE"),
            "docs/checklist.md": (
                "Release Gates & Shipping",
                "Hard invariant",
                "Non-inferiority",
                "Superiority",
                "Operational bound",
                "Shadow",
                "Canary",
                "Progressive rollout",
                "Rollback thresholds",
                "Shipping checklist",
            ),
        }

        self.assertIn("11. Release Gates & Shipping: checklist.md", configuration)
        for chapter, required_markers in chapter_contracts.items():
            content = (REPOSITORY_ROOT / chapter).read_text(encoding="utf-8")
            for marker in required_markers:
                with self.subTest(chapter=chapter, marker=marker):
                    self.assertIn(marker, content)

    def test_site_exposes_the_four_part_programme_and_running_cx_build(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        home_page = (REPOSITORY_ROOT / "docs/index.md").read_text(encoding="utf-8")
        build_page = (REPOSITORY_ROOT / "docs/build-the-system.md").read_text(
            encoding="utf-8"
        )

        for programme_part in (
            "Part I · Evaluation foundations",
            "Part II · Build the CX evaluation system",
            "Part III · Reference library",
            "Part IV · Comparative system studies",
        ):
            with self.subTest(programme_part=programme_part):
                self.assertIn(programme_part, configuration)
                self.assertIn(programme_part, home_page)

        for build_marker in (
            "What works now",
            "The first five cases",
            "OpenAI Agents SDK",
            "Calibration enters in layers",
            "How the system grows",
            "Living regression set",
            "Evaluation programme economics",
            "Programme roadmap",
        ):
            with self.subTest(build_marker=build_marker):
                self.assertIn(build_marker, build_page)

    def test_reference_and_system_study_sections_define_their_contracts(self) -> None:
        references = (REPOSITORY_ROOT / "docs/references.md").read_text(
            encoding="utf-8"
        )
        studies = (REPOSITORY_ROOT / "docs/system-studies.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Primary-source rule", references)
        self.assertIn("Claim ledger", references)
        self.assertIn("OpenAI", references)
        self.assertIn("Anthropic", references)
        self.assertIn("Adopt, adapt, or reject", studies)
        self.assertIn("same CX decision contract", studies)

    def test_frontier_research_is_separated_from_deployment_proof(self) -> None:
        practice = (REPOSITORY_ROOT / "docs/research-to-practice.md").read_text(
            encoding="utf-8"
        )
        source_coverage = (REPOSITORY_ROOT / "docs/source-coverage.md").read_text(
            encoding="utf-8"
        )

        for marker in (
            "Production control",
            "Field evidence",
            "Operational tool",
            "Research or benchmark",
            "Five-Nines",
            "AgentRewardBench",
            "Personalization",
            "Petri",
            "chain-of-thought monitoring",
            "Realtime API",
            "No public deployment proof found",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, practice)

        self.assertIn(
            "Evaluating LLM-Based AI Systems: Research Review and Production Blueprint",
            source_coverage,
        )

    def test_deep_chapters_include_examples_artifacts_and_practice(self) -> None:
        for chapter, required_markers in DEPTH_CHAPTERS.items():
            content = (REPOSITORY_ROOT / chapter).read_text(encoding="utf-8")
            for marker in required_markers:
                with self.subTest(chapter=chapter, marker=marker):
                    self.assertIn(marker, content)

    def test_seven_surfaces_are_preserved_as_independent_dimensions(self) -> None:
        build_page = (REPOSITORY_ROOT / "docs/build-the-system.md").read_text(
            encoding="utf-8"
        )
        for surface in (
            "Outcome",
            "Policy and safety",
            "Tool use and trajectory",
            "Factuality and grounding",
            "Conversation quality",
            "Efficiency",
            "Operations",
        ):
            with self.subTest(surface=surface):
                self.assertIn(surface, build_page)

    def test_courses_page_maps_verified_courses_to_book_practice(self) -> None:
        courses = (REPOSITORY_ROOT / "docs/courses.md").read_text(encoding="utf-8")
        for marker in (
            "Evaluating AI Agents",
            "Building and Evaluating Data Agents",
            "Automated Testing for LLMOps",
            "Evaluating and Debugging Generative AI",
            "Use it with this book",
            "Verified",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, courses)

    def test_courses_page_preserves_the_broader_research_learning_path(self) -> None:
        courses = (REPOSITORY_ROOT / "docs/courses.md").read_text(encoding="utf-8")
        for marker in (
            "AI Evals for Engineers & PMs",
            "LLM Evaluation for Builders",
            "Intro to LangSmith",
            "Hugging Face",
            "Arize",
            "Evidence receipt",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, courses)

    def test_prompt_experiments_have_a_paired_decision_contract(self) -> None:
        build_page = (REPOSITORY_ROOT / "docs/build-the-system.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "Prompt evaluation as a controlled experiment",
            "one intervention",
            "paired",
            "sealed acceptance",
            "prompt version",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, build_page)

    def test_production_outcomes_and_governance_are_explicit(self) -> None:
        production = (REPOSITORY_ROOT / "docs/production-evals.md").read_text(
            encoding="utf-8"
        )
        gate = (REPOSITORY_ROOT / "docs/checklist.md").read_text(encoding="utf-8")

        for marker in (
            "Containment",
            "Deflection",
            "Verified resolution",
            "Adoption",
            "Quality-adjusted business value",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, production)

        for marker in (
            "Governance and ownership",
            "Business or domain owner",
            "Evaluation owner",
            "Release owner",
            "requirements-to-evidence traceability",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, gate)

    def test_internal_markdown_links_resolve(self) -> None:
        markdown_link = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
        for markdown_file in (REPOSITORY_ROOT / "docs").glob("*.md"):
            content = markdown_file.read_text(encoding="utf-8")
            for raw_target in markdown_link.findall(content):
                target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                relative_path = unquote(target.split("#", maxsplit=1)[0])
                if not relative_path:
                    continue
                resolved = (markdown_file.parent / relative_path).resolve()
                with self.subTest(source=markdown_file.name, target=target):
                    self.assertTrue(resolved.exists(), f"broken link: {target}")

    def test_deep_chapters_have_no_unimplemented_scaffold_comments(self) -> None:
        for chapter in EXPECTED_CHAPTERS:
            content = (REPOSITORY_ROOT / chapter).read_text(encoding="utf-8")
            with self.subTest(chapter=chapter):
                self.assertNotRegex(content, r"<!--\s*(?:Add|Replace|TODO|TBD)\b")

    def test_source_coverage_ledger_includes_every_research_theme(self) -> None:
        coverage = (REPOSITORY_ROOT / "docs/source-coverage.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "Fundamentals & evaluation metrics",
            "Benchmarks & contamination",
            "Human evaluation & annotation",
            "LLM-as-a-judge",
            "Robustness & adversarial evaluation",
            "Bias & fairness",
            "Calibration & uncertainty",
            "Prompt evaluation & dataset curation",
            "Reproducibility & statistics",
            "Tooling, MLOps & continuous evaluation",
            "RAG, agents & system evaluation",
            "Interpretability",
            "Safety, RLHF & alignment",
            "Deep Research evaluation",
            "Observability and release gates",
            "Course and project practice",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, coverage)

    def test_source_promises_have_substantive_chapter_treatments(self) -> None:
        rag = (REPOSITORY_ROOT / "docs/rag-research-evals.md").read_text(
            encoding="utf-8"
        )
        interpretability = (REPOSITORY_ROOT / "docs/robustness-safety.md").read_text(
            encoding="utf-8"
        )
        metrics = (REPOSITORY_ROOT / "docs/metrics.md").read_text(encoding="utf-8")
        drills = (REPOSITORY_ROOT / "docs/interview-drills.md").read_text(
            encoding="utf-8"
        )

        for marker in (
            "Humanity’s Last Exam",
            "GAIA answer-key leakage",
            "PersonQA",
            "Long-output adaptation",
            "Deployed versus capability-eliciting",
        ):
            with self.subTest(chapter="rag", marker=marker):
                self.assertIn(marker, rag)

        for marker in (
            "Interpretability versus explainability",
            "Evaluate a mechanistic interpretability method",
            "causal completeness",
            "false discoveries",
            "toy mechanism",
        ):
            with self.subTest(chapter="interpretability", marker=marker):
                self.assertIn(marker, interpretability)

        for marker in (
            "Worked calibration example",
            "Brier = 0.23725",
            "ECE = 0.075",
            "probability-calibration-v1.json",
        ):
            with self.subTest(chapter="metrics", marker=marker):
                self.assertIn(marker, metrics)

        whiteboards = drills.split("## Whiteboard drills", maxsplit=1)[1].split(
            "## Senior scenario drills", maxsplit=1
        )[0]
        self.assertEqual(len(re.findall(r"(?m)^### ", whiteboards)), 8)
        self.assertIn("### Perturbation harness", whiteboards)
        self.assertIn("### Atomic factuality", whiteboards)

    def test_deep_research_treatment_has_configuration_examples_and_receipts(
        self,
    ) -> None:
        rag = (REPOSITORY_ROOT / "docs/rag-research-evals.md").read_text(
            encoding="utf-8"
        )

        for marker in (
            "26.6%",
            "74.29%",
            "67.36%",
            "72.57%",
            "1,266",
            "51.5%",
            "95% bootstrap confidence intervals",
            "StrongReject",
            "BBQ",
            "Worked example: a long report passes the short answer and fails the report",
            "Worked example: deployed and capability-eliciting configurations",
            "Artifact: Deep Research evaluation claim record",
            "Exercise: audit a research-agent claim",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, rag)

        self.assertIn("atomic_claim_links: 3", rag)
        self.assertIn("entailing: 1", rag)

    def test_visible_contracts_and_examples_are_internally_consistent(self) -> None:
        dataset = (REPOSITORY_ROOT / "docs/dataset-design.md").read_text(
            encoding="utf-8"
        )
        production = (REPOSITORY_ROOT / "docs/production-evals.md").read_text(
            encoding="utf-8"
        )
        references = (REPOSITORY_ROOT / "docs/references.md").read_text(
            encoding="utf-8"
        )
        contract = (REPOSITORY_ROOT / "evals/cx-support/contracts/refund_v0.json").read_text(
            encoding="utf-8"
        )

        self.assertIn("Access-oriented stores and overlays", dataset)
        self.assertIn("Safety is an overlay", dataset)
        self.assertIn("1,000 matured eligible conversations in each arm", production)
        self.assertIn("The agent receives only the customer utterance", contract)
        self.assertIn(
            "in-your-repository/managing-protected-branches/about-protected-branches",
            references,
        )


class PublishingWorkflowTests(unittest.TestCase):
    def test_local_preview_uses_the_safari_compatible_localhost_url(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        makefile = (REPOSITORY_ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("http://localhost:8797/litp2l-evals-primer/", readme)
        self.assertNotIn("Open <http://127.0.0.1", readme)
        self.assertIn("mkdocs serve --dev-addr localhost:8797", makefile)

    def test_pages_workflow_has_required_permissions_and_build(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/pages.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("uv run mkdocs build --strict", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)

    def test_book_does_not_reference_private_parent_content(self) -> None:
        markdown_files = tuple((REPOSITORY_ROOT / "docs").glob("*.md"))

        for markdown_file in markdown_files:
            content = markdown_file.read_text(encoding="utf-8")
            with self.subTest(markdown_file=markdown_file.name):
                self.assertNotIn("../private", content)
                self.assertNotIn("litp2l/private", content)


class BuiltSiteTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("uv"), "uv is required for the build test")
    def test_strict_build_produces_green_home_page(self) -> None:
        with tempfile.TemporaryDirectory() as site_directory:
            subprocess.run(
                (
                    "uv",
                    "run",
                    "mkdocs",
                    "build",
                    "--strict",
                    "--site-dir",
                    site_directory,
                ),
                cwd=REPOSITORY_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            home_page = (Path(site_directory) / "index.html").read_text(
                encoding="utf-8"
            )

        self.assertIn("Evals Primer", home_page)
        self.assertTrue(re.search(r"data-md-color-primary=\"green\"", home_page))

    @unittest.skipUnless(shutil.which("uv"), "uv is required for the build test")
    def test_strict_build_wraps_math_for_browser_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as site_directory:
            subprocess.run(
                (
                    "uv",
                    "run",
                    "mkdocs",
                    "build",
                    "--strict",
                    "--site-dir",
                    site_directory,
                ),
                cwd=REPOSITORY_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            metrics_page = (Path(site_directory) / "metrics/index.html").read_text(
                encoding="utf-8"
            )

        self.assertIn('class="arithmatex"', metrics_page)
        self.assertIn("javascripts/mathjax.js", metrics_page)
        self.assertIn("tex-mml-chtml.js", metrics_page)


if __name__ == "__main__":
    unittest.main()
