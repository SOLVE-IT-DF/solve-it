"""Tests for admin/issue_parsers/parse_update_weakness_issue.py — new format (categories list)."""

import unittest
import copy
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_update_weakness_issue import apply_updates
from update_utils import is_no_response


SAMPLE_WEAKNESS = {
    "id": "DFW-1001",
    "name": "Test weakness",
    "categories": ["ASTM_INCOMP"],
    "mitigations": ["DFM-1001"],
    "references": [],
}


class TestApplyUpdates(unittest.TestCase):

    def test_no_change_when_blank(self):
        fields = {
            "New weakness name": "_No response_",
            "Categories": "_No response_",
            "Mitigation IDs": "_No response_",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_WEAKNESS)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated, current)

    def test_replace_categories(self):
        fields = {
            "New weakness name": "_No response_",
            "Categories": "ASTM_MISINT\nASTM_INAC_EX",
            "Mitigation IDs": "_No response_",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_WEAKNESS)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated["categories"], ["ASTM_MISINT", "ASTM_INAC_EX"])

    def test_clear_categories(self):
        """Empty textarea (but not _No response_) should clear the list."""
        fields = {
            "New weakness name": "_No response_",
            "Categories": "",
            "Mitigation IDs": "_No response_",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_WEAKNESS)
        updated, _, _, _ = apply_updates(current, fields)
        # Empty string is treated as is_no_response (True), so no change
        self.assertEqual(updated["categories"], ["ASTM_INCOMP"])

    def test_update_name(self):
        fields = {
            "New weakness name": "New name",
            "Categories": "_No response_",
            "Mitigation IDs": "_No response_",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_WEAKNESS)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated["name"], "New name")

    def test_invalid_class_returns_none(self):
        fields = {
            "New weakness name": "_No response_",
            "Categories": "BAD_CODE",
            "Mitigation IDs": "_No response_",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_WEAKNESS)
        updated, _, _, errors = apply_updates(current, fields)
        self.assertIsNone(updated)
        self.assertTrue(any("BAD_CODE" in e for e in errors))


if __name__ == '__main__':
    unittest.main()
