"""Tests for admin/issue_parsers/parse_mitigation_issue.py."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_mitigation_issue import build_mitigation_json, build_comment, KNOWN_FIELD_LABELS
from parse_technique_issue import unknown_field_labels


def _make_fields(name="Test mitigation", description="", weaknesses=""):
    return {
        "Mitigation name": name,
        "Description": description,
        "Existing weakness IDs": weaknesses,
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


class TestBuildCommentWarnings(unittest.TestCase):

    def _comment(self, fields):
        mitigation, match_report, new_citations, ref_warnings = build_mitigation_json(fields)
        return build_comment(mitigation, fields, match_report, new_citations, ref_warnings)

    def test_orphan_warning_when_no_weaknesses(self):
        comment = self._comment(_make_fields())
        self.assertIn("No weaknesses linked", comment)
        self.assertIn("orphan", comment)

    def test_no_orphan_warning_when_weaknesses_given(self):
        comment = self._comment(_make_fields(weaknesses="DFW-1154"))
        self.assertNotIn("No weaknesses linked", comment)
        self.assertIn("Relevant weaknesses (1)", comment)
        self.assertIn("DFW-1154", comment)

    def test_unrecognised_field_warning(self):
        fields = _make_fields()
        del fields["Existing weakness IDs"]
        fields["Weaknesses this applies to"] = "DFW-1154"
        comment = self._comment(fields)
        self.assertIn("Unrecognised fields", comment)
        self.assertIn("`Weaknesses this applies to`", comment)
        # The unmatched field also means no weaknesses were linked
        self.assertIn("No weaknesses linked", comment)

    def test_no_unrecognised_field_warning_for_form_fields(self):
        fields = _make_fields(weaknesses="DFW-1154")
        fields["Any other notes"] = "some notes"
        comment = self._comment(fields)
        self.assertNotIn("Unrecognised fields", comment)


class TestUnknownFieldLabels(unittest.TestCase):

    def test_all_known(self):
        self.assertEqual(unknown_field_labels(_make_fields(), KNOWN_FIELD_LABELS), [])

    def test_unknown_reported(self):
        fields = _make_fields()
        fields["Weaknesses this applies to"] = "DFW-1154"
        self.assertEqual(unknown_field_labels(fields, KNOWN_FIELD_LABELS),
                         ["Weaknesses this applies to"])


if __name__ == '__main__':
    unittest.main()
