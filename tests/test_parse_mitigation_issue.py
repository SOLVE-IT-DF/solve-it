"""Tests for admin/issue_parsers/parse_mitigation_issue.py."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_mitigation_issue import build_mitigation_json


def _make_fields(name="Test mitigation", description=""):
    return {
        "Mitigation name": name,
        "Description": description,
        "Existing weakness IDs": "",
        "Linked technique": "",
        "References": "",
    }


class TestBuildMitigationJson(unittest.TestCase):

    def test_basic_mitigation(self):
        fields = _make_fields()
        mitigation, _, _, _ = build_mitigation_json(fields)
        self.assertEqual(mitigation["id"], "DFM-____")
        self.assertEqual(mitigation["name"], "Test mitigation")

    def test_description_included(self):
        fields = _make_fields(description="A test description")
        mitigation, _, _, _ = build_mitigation_json(fields)
        self.assertEqual(mitigation["description"], "A test description")

    def test_description_empty_by_default(self):
        fields = _make_fields()
        mitigation, _, _, _ = build_mitigation_json(fields)
        self.assertEqual(mitigation["description"], "")


if __name__ == '__main__':
    unittest.main()
