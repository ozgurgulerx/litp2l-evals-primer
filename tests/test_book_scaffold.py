"""Contract tests for the Evals Primer book scaffold."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CHAPTERS = (
    "docs/index.md",
    "docs/foundations.md",
    "docs/dataset-design.md",
    "docs/metrics.md",
    "docs/llm-as-a-judge.md",
    "docs/production-evals.md",
    "docs/checklist.md",
)


class BookConfigurationTests(unittest.TestCase):
    def test_configuration_uses_green_material_theme(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")

        self.assertRegex(configuration, r"(?m)^\s+name:\s+material\s*$")
        self.assertRegex(configuration, r"(?m)^\s+primary:\s+green\s*$")
        self.assertRegex(configuration, r"(?m)^\s+accent:\s+light green\s*$")

    def test_navigation_references_every_chapter(self) -> None:
        configuration = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")

        for chapter in EXPECTED_CHAPTERS:
            relative_chapter = chapter.removeprefix("docs/")
            with self.subTest(chapter=relative_chapter):
                self.assertIn(relative_chapter, configuration)
                self.assertTrue((REPOSITORY_ROOT / chapter).is_file())


class PublishingWorkflowTests(unittest.TestCase):
    def test_pages_workflow_has_required_permissions_and_build(self) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github/workflows/pages.yml"
        ).read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
