"""Exercise the book's link-validation configuration in isolated tiny sites."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class LinkValidationTests(unittest.TestCase):
    def build_fixture(self, target):
        configuration = yaml.safe_load((ROOT / "mkdocs.yml").read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "docs/index.md").write_text(f"# Home\n\n[Exercise]({target})\n")
            (root / "docs/lesson.md").write_text("# Lesson\n\n## Worked solution\n")
            (root / "mkdocs.yml").write_text(yaml.safe_dump({
                "site_name": "Link validation fixture",
                "validation": configuration.get("validation", {}),
            }))
            return subprocess.run(
                [sys.executable, "-m", "mkdocs", "build", "--strict"],
                cwd=root, capture_output=True, text=True, timeout=30, check=False,
            )

    def test_valid_exercise_anchor_builds(self):
        result = self.build_fixture("lesson.md#worked-solution")
        self.assertEqual(0, result.returncode, result.stderr)

    def test_missing_exercise_anchor_blocks_strict_build(self):
        result = self.build_fixture("lesson.md#missing-solution")
        self.assertNotEqual(0, result.returncode, result.stderr)
        self.assertIn("missing-solution", result.stderr)

    def test_missing_exercise_page_blocks_strict_build(self):
        result = self.build_fixture("missing.md")
        self.assertNotEqual(0, result.returncode, result.stderr)
        self.assertIn("missing.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
