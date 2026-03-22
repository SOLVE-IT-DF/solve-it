"""Tests for admin/issue_parsers/parse_trwm_submission.py."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_trwm_submission import (
    normalize_to_kb_schema, validate_submission,
    TECHNIQUE_FIELDS, WEAKNESS_FIELDS, MITIGATION_FIELDS,
)


class TestNormalizeReferences(unittest.TestCase):
    """References must be lists of dicts; bare strings are invalid."""

    def test_bare_strings_filtered_out(self):
        item = {"id": "DFT-9999", "name": "Test", "references": ["timeline"]}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [])

    def test_dict_references_preserved(self):
        ref = {"DFCite_id": "DFCite-1001", "relevance_summary_280": "Relevant"}
        item = {"id": "DFT-9999", "name": "Test", "references": [ref]}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [ref])

    def test_mixed_list_keeps_only_dicts(self):
        ref = {"DFCite_id": "DFCite-1001", "relevance_summary_280": "Relevant"}
        item = {"id": "DFT-9999", "name": "Test", "references": ["bad", ref, 42]}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [ref])

    def test_empty_references_unchanged(self):
        item = {"id": "DFT-9999", "name": "Test", "references": []}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [])

    def test_missing_references_defaults_to_empty(self):
        item = {"id": "DFT-9999", "name": "Test"}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [])

    def test_weakness_references_filtered(self):
        item = {"id": "DFW-9999", "name": "Test", "references": ["bad"]}
        result = normalize_to_kb_schema(item, WEAKNESS_FIELDS)
        self.assertEqual(result["references"], [])

    def test_mitigation_references_filtered(self):
        item = {"id": "DFM-9999", "name": "Test", "references": ["bad"]}
        result = normalize_to_kb_schema(item, MITIGATION_FIELDS)
        self.assertEqual(result["references"], [])


class TestValidateSubmissionReferences(unittest.TestCase):
    """validate_submission should warn when non-dict references are present."""

    def test_warns_on_bare_string_references(self):
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {
                    "id": "DFT-temp-0001",
                    "name": "Test technique",
                    "description": "desc",
                    "weaknesses": ["DFW-temp-0001"],
                    "references": ["timeline"],
                }
            },
            "weaknesses": {
                "DFW-temp-0001": {
                    "id": "DFW-temp-0001",
                    "name": "Test weakness",
                    "categories": ["ASTM_INCOMP"],
                    "mitigations": [],
                    "references": [],
                }
            },
            "mitigations": {},
        }
        new_items = {
            "techniques": [trwm_data["techniques"]["DFT-temp-0001"]],
            "weaknesses": [trwm_data["weaknesses"]["DFW-temp-0001"]],
            "mitigations": [],
        }
        notes = validate_submission(trwm_data, new_items)
        warning_msgs = [msg for level, msg in notes if level == "warning"]
        self.assertTrue(
            any("references" in msg and "non-dict" in msg for msg in warning_msgs),
            f"Expected a non-dict references warning, got: {warning_msgs}"
        )

    def test_no_warning_for_valid_references(self):
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {
                    "id": "DFT-temp-0001",
                    "name": "Test",
                    "description": "desc",
                    "weaknesses": [],
                    "references": [{"DFCite_id": "DFCite-1001"}],
                }
            },
            "weaknesses": {},
            "mitigations": {},
        }
        new_items = {
            "techniques": [trwm_data["techniques"]["DFT-temp-0001"]],
            "weaknesses": [],
            "mitigations": [],
        }
        notes = validate_submission(trwm_data, new_items)
        warning_msgs = [msg for level, msg in notes if level == "warning"]
        self.assertFalse(
            any("non-dict" in msg for msg in warning_msgs),
            f"Unexpected non-dict warning: {warning_msgs}"
        )


if __name__ == '__main__':
    unittest.main()
