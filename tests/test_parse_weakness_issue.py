"""Tests for admin/issue_parsers/parse_weakness_issue.py — new format (categories list)."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_weakness_issue import build_weakness_json, parse_categories


class TestParseWeaknessClasses(unittest.TestCase):

    def test_parse_single_class(self):
        valid, invalid = parse_categories("ASTM_INCOMP")
        self.assertEqual(valid, ["ASTM_INCOMP"])
        self.assertEqual(invalid, [])

    def test_parse_multiple_classes(self):
        valid, invalid = parse_categories("ASTM_INCOMP\nASTM_MISINT")
        self.assertEqual(valid, ["ASTM_INCOMP", "ASTM_MISINT"])
        self.assertEqual(invalid, [])

    def test_parse_empty(self):
        valid, invalid = parse_categories("")
        self.assertEqual(valid, [])
        self.assertEqual(invalid, [])

    def test_parse_reports_invalid(self):
        valid, invalid = parse_categories("ASTM_INCOMP\nINVALID\nASTM_MISINT")
        self.assertEqual(valid, ["ASTM_INCOMP", "ASTM_MISINT"])
        self.assertEqual(invalid, ["INVALID"])

    def test_parse_strips_whitespace(self):
        valid, invalid = parse_categories("  ASTM_INCOMP  \n  ASTM_MISINT  ")
        self.assertEqual(valid, ["ASTM_INCOMP", "ASTM_MISINT"])
        self.assertEqual(invalid, [])


def _make_fields(classes_text="", name="Test weakness", description=""):
    return {
        "Weakness name": name,
        "Description": description,
        "Categories": classes_text,
        "Existing mitigation IDs": "",
        "Techniques this applies to": "",
        "References": "",
    }


class TestBuildWeaknessJson(unittest.TestCase):

    def test_build_weakness_json_single_class(self):
        fields = _make_fields("ASTM_INCOMP")
        weakness, _, _, _ = build_weakness_json(fields)
        self.assertEqual(weakness["categories"], ["ASTM_INCOMP"])

    def test_build_weakness_json_multiple_classes(self):
        fields = _make_fields("ASTM_INCOMP\nASTM_MISINT")
        weakness, _, _, _ = build_weakness_json(fields)
        self.assertEqual(weakness["categories"], ["ASTM_INCOMP", "ASTM_MISINT"])

    def test_build_weakness_json_none_checked(self):
        fields = _make_fields("")
        weakness, _, _, _ = build_weakness_json(fields)
        self.assertEqual(weakness["categories"], [])

    def test_build_weakness_json_all_classes(self):
        all_classes = "ASTM_INCOMP\nASTM_INAC_EX\nASTM_INAC_AS\nASTM_INAC_ALT\nASTM_INAC_COR\nASTM_MISINT"
        fields = _make_fields(all_classes)
        weakness, _, _, _ = build_weakness_json(fields)
        self.assertEqual(len(weakness["categories"]), 6)

    def test_output_has_categories_key(self):
        fields = _make_fields("ASTM_INCOMP")
        weakness, _, _, _ = build_weakness_json(fields)
        self.assertIn("categories", weakness)
        self.assertNotIn("INCOMP", weakness)

    def test_invalid_class_returns_none(self):
        fields = _make_fields("ASTM_INCOMP\nBAD_CODE")
        weakness, _, _, errors = build_weakness_json(fields)
        self.assertIsNone(weakness)
        self.assertTrue(any("BAD_CODE" in e for e in errors))

    def test_description_included(self):
        fields = _make_fields("ASTM_INCOMP", description="A test description")
        weakness, _, _, _ = build_weakness_json(fields)
        self.assertEqual(weakness["description"], "A test description")

    def test_description_empty_by_default(self):
        fields = _make_fields("ASTM_INCOMP")
        weakness, _, _, _ = build_weakness_json(fields)
        self.assertEqual(weakness["description"], "")


if __name__ == '__main__':
    unittest.main()
