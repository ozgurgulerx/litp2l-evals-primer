"""Keep the intentionally unsafe shipping example visibly bounded and executable."""

import re
import unittest
from pathlib import Path

CHAPTER = Path(__file__).resolve().parents[1] / "docs/checklist.md"


class ShippingExampleTests(unittest.TestCase):
    def test_counterexample_is_warned_before_code(self):
        chapter = CHAPTER.read_text(encoding="utf-8")
        warning = '!!! danger "Known-bad teaching example—not a deployment gate"'
        self.assertIn(warning, chapter)
        self.assertLess(chapter.index(warning), chapter.index("def release_action("))

    def test_published_probes_reproduce_both_false_promotions(self):
        blocks = re.findall(r"```python\n(.*?)\n```", CHAPTER.read_text(), re.DOTALL)
        self.assertEqual(2, len(blocks))
        namespace = {}
        for block in blocks:
            # Execute only this fixed, reviewed repository chapter, never uploaded artifacts.
            exec(compile(block, str(CHAPTER), "exec"), namespace)  # noqa: S102
        self.assertEqual("canary", namespace["nan_result"]["action"])
        self.assertEqual("canary", namespace["unqualified_result"]["action"])
        self.assertEqual("block", namespace["missing_cost_result"]["action"])


if __name__ == "__main__":
    unittest.main()
