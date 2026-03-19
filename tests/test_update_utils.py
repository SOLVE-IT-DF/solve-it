"""Tests for admin/issue_parsers/update_utils.py — new format."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from update_utils import is_no_response, build_change_summary


class TestIsNoResponse(unittest.TestCase):

    def test_is_no_response_blank(self):
        self.assertTrue(is_no_response(""))

    def test_is_no_response_github_default(self):
        self.assertTrue(is_no_response("_No response_"))

    def test_is_no_response_with_value(self):
        self.assertFalse(is_no_response("Some value"))


class TestBuildChangeSummary(unittest.TestCase):

    def test_change_summary_categories_added(self):
        before = {"categories": ["ASTM_INCOMP"]}
        after = {"categories": ["ASTM_INCOMP", "ASTM_MISINT"]}
        result = build_change_summary(before, after)
        self.assertTrue(any("added" in line and "ASTM_MISINT" in line for line in result))

    def test_change_summary_categories_removed(self):
        before = {"categories": ["ASTM_INCOMP", "ASTM_MISINT"]}
        after = {"categories": ["ASTM_INCOMP"]}
        result = build_change_summary(before, after)
        self.assertTrue(any("removed" in line and "ASTM_MISINT" in line for line in result))

    def test_change_summary_list_added(self):
        before = {"mitigations": ["DFM-1001"]}
        after = {"mitigations": ["DFM-1001", "DFM-1002"]}
        result = build_change_summary(before, after)
        self.assertTrue(any("added" in line and "DFM-1002" in line for line in result))

    def test_change_summary_list_removed(self):
        before = {"mitigations": ["DFM-1001", "DFM-1002"]}
        after = {"mitigations": ["DFM-1001"]}
        result = build_change_summary(before, after)
        self.assertTrue(any("removed" in line and "DFM-1002" in line for line in result))

    def test_change_summary_no_changes(self):
        d = {"name": "test", "categories": ["ASTM_INCOMP"]}
        result = build_change_summary(d, d)
        self.assertEqual(result, ["No changes detected."])

    def test_change_summary_scalar_change(self):
        before = {"name": "old name"}
        after = {"name": "new name"}
        result = build_change_summary(before, after)
        self.assertTrue(any("name" in line and "changed" in line for line in result))


if __name__ == '__main__':
    unittest.main()
