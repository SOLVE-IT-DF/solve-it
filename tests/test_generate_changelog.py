"""Tests for admin/generate_changelog.py: duplicate handling and source labels."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
from generate_changelog import drop_duplicates, render_markdown


def entry(commit="aaaaaaa", id="DFT-1212", action="added", source="trwm", date="2026-10-19"):
    return {"date": date, "action": action, "type": "technique", "id": id,
            "name": "Create a case-specific keyword list", "commit": commit,
            "source": source, "issue": None}


class TestDropDuplicates(unittest.TestCase):

    def test_repeats_of_same_commit_item_and_action_are_removed(self):
        self.assertEqual(len(drop_duplicates([entry(), entry(), entry()])), 1)

    def test_same_item_in_a_different_commit_is_kept(self):
        self.assertEqual(len(drop_duplicates([entry(commit="aaaaaaa"), entry(commit="bbbbbbb")])), 2)

    def test_same_commit_changing_two_items_is_kept(self):
        self.assertEqual(len(drop_duplicates([entry(id="DFT-1211"), entry(id="DFT-1212")])), 2)

    def test_add_and_delete_in_one_commit_are_both_kept(self):
        self.assertEqual(len(drop_duplicates([entry(action="added"), entry(action="deleted")])), 2)

    def test_first_occurrence_and_order_are_kept(self):
        first, other = entry(id="DFT-1211"), entry(id="DFT-1212")
        self.assertEqual(drop_duplicates([first, other, dict(first)]), [first, other])


class TestSourceLabel(unittest.TestCase):

    def render(self, source):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CHANGELOG_DATA.md"
            render_markdown([entry(source=source)], path)
            return path.read_text()

    def test_trwm_is_labelled(self):
        self.assertIn("Added technique (TRWM):", self.render("trwm"))

    def test_autoimplement_is_not_labelled(self):
        text = self.render("autoimplement")
        self.assertIn("Added technique:", text)
        self.assertNotIn("AUTOIMPLEMENT", text)

    def test_manual_is_not_labelled(self):
        self.assertIn("Added technique:", self.render("manual"))


if __name__ == "__main__":
    unittest.main()
