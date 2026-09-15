"""Tests for the `_none_` sentinel that empties a list on the update forms.

A blank field means "leave this alone", so without a sentinel a contributor who
removes the last entry of a list has no way to say so and the change is silently
dropped. `_none_` means "replace this list with an empty one".
"""

import unittest
import copy
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from update_utils import is_clear_request, is_no_response
import parse_update_technique_issue
import parse_update_weakness_issue
import parse_update_mitigation_issue


SAMPLE_TECHNIQUE = {
    "id": "DFT-1001",
    "name": "Test technique",
    "description": "Original description",
    "synonyms": ["alpha", "beta"],
    "details": "Original details",
    "subtechniques": ["DFT-1002"],
    "examples": ["Some tool"],
    "weaknesses": ["DFW-1001"],
    "CASE_input_classes": ["https://ontology.unifiedcyberontology.org/uco/observable/File"],
    "CASE_output_classes": ["https://ontology.unifiedcyberontology.org/uco/observable/File"],
    "references": [{"DFCite_id": "DFCite-1001", "relevance_summary_280": "why"}],
}

SAMPLE_WEAKNESS = {
    "id": "DFW-1001",
    "name": "Test weakness",
    "description": "Original description",
    "categories": ["ASTM_INCOMP"],
    "mitigations": ["DFM-1001"],
    "references": [{"DFCite_id": "DFCite-1001", "relevance_summary_280": "why"}],
}

SAMPLE_MITIGATION = {
    "id": "DFM-1001",
    "name": "Test mitigation",
    "description": "Original description",
    "references": [{"DFCite_id": "DFCite-1001", "relevance_summary_280": "why"}],
}


class TestIsClearRequest(unittest.TestCase):

    def test_sentinel_recognised(self):
        self.assertTrue(is_clear_request("_none_"))

    def test_sentinel_tolerates_surrounding_whitespace(self):
        self.assertTrue(is_clear_request("  _none_\n"))

    def test_sentinel_is_case_insensitive(self):
        self.assertTrue(is_clear_request("_None_"))

    def test_blank_is_not_a_clear_request(self):
        self.assertFalse(is_clear_request(""))

    def test_github_default_is_not_a_clear_request(self):
        self.assertFalse(is_clear_request("_No response_"))

    def test_ordinary_content_is_not_a_clear_request(self):
        self.assertFalse(is_clear_request("DFW-1001"))

    def test_sentinel_among_other_lines_is_not_a_clear_request(self):
        # Only a field consisting of the sentinel alone clears the list; a line
        # of real content alongside it must not silently discard that content.
        self.assertFalse(is_clear_request("_none_\nDFW-1001"))

    def test_sentinel_is_not_read_as_blank(self):
        # The two helpers must not both claim the same value, or the clear
        # branch would be unreachable in the parsers.
        self.assertFalse(is_no_response("_none_"))


class TestTechniqueClearing(unittest.TestCase):

    def _apply(self, field, value):
        current = copy.deepcopy(SAMPLE_TECHNIQUE)
        updated, _, _, _ = parse_update_technique_issue.apply_updates(current, {field: value})
        return updated

    def test_clears_synonyms(self):
        self.assertEqual(self._apply("Synonyms", "_none_")["synonyms"], [])

    def test_clears_examples(self):
        self.assertEqual(self._apply("Examples", "_none_")["examples"], [])

    def test_clears_subtechniques(self):
        self.assertEqual(self._apply("Subtechnique IDs", "_none_")["subtechniques"], [])

    def test_clears_weaknesses(self):
        self.assertEqual(self._apply("Weakness IDs", "_none_")["weaknesses"], [])

    def test_clears_input_classes(self):
        self.assertEqual(self._apply("Ontology input classes", "_none_")["CASE_input_classes"], [])

    def test_clears_output_classes(self):
        self.assertEqual(self._apply("Ontology output classes", "_none_")["CASE_output_classes"], [])

    def test_clears_references(self):
        self.assertEqual(self._apply("References", "_none_")["references"], [])

    def test_omitted_field_still_leaves_list_alone(self):
        updated = self._apply("Synonyms", "_No response_")
        self.assertEqual(updated["synonyms"], ["alpha", "beta"])

    def test_sentinel_does_not_become_a_list_entry(self):
        self.assertNotIn("_none_", self._apply("Synonyms", "_none_")["synonyms"])

    def test_clears_details(self):
        self.assertEqual(self._apply("New details", "_none_")["details"], "")

    def test_clears_description(self):
        self.assertEqual(self._apply("New description", "_none_")["description"], "")

    def test_clearing_one_list_leaves_the_others_untouched(self):
        updated = self._apply("Synonyms", "_none_")
        self.assertEqual(updated["weaknesses"], ["DFW-1001"])
        self.assertEqual(updated["examples"], ["Some tool"])


class TestWeaknessClearing(unittest.TestCase):

    def _apply(self, field, value):
        current = copy.deepcopy(SAMPLE_WEAKNESS)
        updated, _, _, _ = parse_update_weakness_issue.apply_updates(current, {field: value})
        return updated

    def test_clears_categories(self):
        self.assertEqual(self._apply("Categories", "_none_")["categories"], [])

    def test_clears_mitigations(self):
        self.assertEqual(self._apply("Mitigation IDs", "_none_")["mitigations"], [])

    def test_clears_references(self):
        self.assertEqual(self._apply("References", "_none_")["references"], [])

    def test_clearing_categories_skips_class_validation(self):
        # `_none_` is not an ASTM code, so it must be handled before the
        # category validator rather than rejected as an unrecognised class.
        current = copy.deepcopy(SAMPLE_WEAKNESS)
        updated, _, _, errors = parse_update_weakness_issue.apply_updates(current, {"Categories": "_none_"})
        self.assertIsNotNone(updated)
        self.assertEqual(errors, [])


    def test_clears_description(self):
        self.assertEqual(self._apply("New description", "_none_")["description"], "")


class TestMitigationClearing(unittest.TestCase):

    def test_clears_description(self):
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = parse_update_mitigation_issue.apply_updates(current, {"New description": "_none_"})
        self.assertEqual(updated["description"], "")

    def test_clears_references(self):
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = parse_update_mitigation_issue.apply_updates(current, {"References": "_none_"})
        self.assertEqual(updated["references"], [])

    def test_blank_leaves_references_alone(self):
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = parse_update_mitigation_issue.apply_updates(current, {"References": "_No response_"})
        self.assertEqual(len(updated["references"]), 1)


if __name__ == '__main__':
    unittest.main()
