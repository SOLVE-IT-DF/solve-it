"""
Regression tests for the SOLVE-IT HTML explorer generator.

Covers:
- Deep linking with both old (T/W/M) and new (DFT-/DFW-/DFM-) ID prefixes
- Contributor credit extraction across file renames
"""

import unittest
import re
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
from generate_html_from_kb import extract_git_credits, _build_rename_map

REPO_ROOT = Path(os.path.dirname(__file__)).parent


class TestDeepLinks(unittest.TestCase):
    """Verify that the generated HTML handles both old and new-style deep links."""

    @classmethod
    def setUpClass(cls):
        html_path = REPO_ROOT / "solveit-viewer.html"
        if not html_path.exists():
            raise unittest.SkipTest("solveit-viewer.html not found — run generate_html_from_kb.py first")
        cls.html = html_path.read_text()

    def test_new_prefix_deep_links(self):
        """New-style DFT-/DFW-/DFM- hash links should be handled."""
        self.assertIn("startsWith('DFT-')", self.html)
        self.assertIn("startsWith('DFW-')", self.html)
        self.assertIn("startsWith('DFM-')", self.html)

    def test_old_prefix_redirect(self):
        """Old-style T/W/M hash links should be redirected to new prefixes."""
        # The JS should detect old prefixes and rewrite the hash
        self.assertRegex(self.html, r"/\^\[TWM\]\\d/")
        # Should map old prefixes to new ones
        self.assertIn("T:'DFT-'", self.html)
        self.assertIn("W:'DFW-'", self.html)
        self.assertIn("M:'DFM-'", self.html)

    def test_old_prefix_uses_replace(self):
        """Old-prefix redirect should use location.replace to avoid polluting history."""
        self.assertIn("location.replace('#' + id)", self.html)


class TestGitCredits(unittest.TestCase):
    """Verify contributor extraction follows file renames and doesn't regress."""

    @classmethod
    def setUpClass(cls):
        cls.credits = extract_git_credits(REPO_ROOT)
        cls.all_contributors = set()
        for v in cls.credits.values():
            cls.all_contributors.update(v["contributors"])

    def test_rename_map_populated(self):
        """The rename map should detect the T->DFT, W->DFW, M->DFM renames."""
        rename_map = _build_rename_map(REPO_ROOT)
        self.assertGreater(len(rename_map), 0)
        # Spot-check a known rename
        self.assertEqual(rename_map.get("T1134"), "DFT-1134")

    def test_known_contributor_credited_across_rename(self):
        """Céline Vanini authored T1134 (now DFT-1134) and must appear as contributor."""
        item = self.credits.get("DFT-1134", {})
        self.assertIn("Céline Vanini", item.get("contributors", []))

    def test_unique_contributor_count_does_not_regress(self):
        """Total unique contributors should not decrease (currently 7)."""
        self.assertGreaterEqual(len(self.all_contributors), 7,
            f"Unique contributor count dropped to {len(self.all_contributors)}: "
            f"{sorted(self.all_contributors)}")

    def test_total_contributor_entries_do_not_regress(self):
        """Total contributor entries across all items should not decrease (currently 961)."""
        total = sum(len(v["contributors"]) for v in self.credits.values())
        self.assertGreaterEqual(total, 961,
            f"Total contributor entries dropped to {total} — "
            f"rename following may be broken")


if __name__ == '__main__':
    unittest.main()
