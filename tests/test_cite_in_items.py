"""
Tests for the cite-in-items feature in parse_reference_issue.py.

Covers parse_cite_in_items(), validate_cite_items_exist(), and
the cite-in-items section in build_comment().
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parse_reference_issue import (
    build_comment,
    parse_cite_in_items,
    validate_cite_items_exist,
)


class TestParseCiteInItems(unittest.TestCase):

    def test_single_item(self):
        items, errors = parse_cite_in_items("DFT-1001 | Describes the technique")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["item_id"], "DFT-1001")
        self.assertEqual(items[0]["relevance_summary"], "Describes the technique")
        self.assertEqual(errors, [])

    def test_multiple_items(self):
        raw = "DFT-1001 | Reason one\nDFW-1002 | Reason two\nDFM-1003 | Reason three"
        items, errors = parse_cite_in_items(raw)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["item_id"], "DFT-1001")
        self.assertEqual(items[1]["item_id"], "DFW-1002")
        self.assertEqual(items[2]["item_id"], "DFM-1003")
        self.assertEqual(errors, [])

    def test_empty_string(self):
        items, errors = parse_cite_in_items("")
        self.assertEqual(items, [])
        self.assertEqual(errors, [])

    def test_no_response(self):
        items, errors = parse_cite_in_items("_No response_")
        self.assertEqual(items, [])
        self.assertEqual(errors, [])

    def test_none_input(self):
        items, errors = parse_cite_in_items(None)
        self.assertEqual(items, [])
        self.assertEqual(errors, [])

    def test_blank_lines_ignored(self):
        raw = "DFT-1001 | Reason\n\n\nDFW-1002 | Another reason\n"
        items, errors = parse_cite_in_items(raw)
        self.assertEqual(len(items), 2)
        self.assertEqual(errors, [])

    def test_invalid_id_format(self):
        items, errors = parse_cite_in_items("INVALID-123 | Some reason")
        self.assertEqual(items, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("Invalid item ID format", errors[0])

    def test_missing_pipe(self):
        items, errors = parse_cite_in_items("DFT-1001 Some reason without pipe")
        self.assertEqual(items, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing `|` separator", errors[0])

    def test_relevance_too_long(self):
        long_text = "x" * 281
        items, errors = parse_cite_in_items(f"DFT-1001 | {long_text}")
        self.assertEqual(items, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("exceeds 280 chars", errors[0])

    def test_relevance_exactly_280(self):
        text = "x" * 280
        items, errors = parse_cite_in_items(f"DFT-1001 | {text}")
        self.assertEqual(len(items), 1)
        self.assertEqual(errors, [])

    def test_whitespace_stripping(self):
        items, errors = parse_cite_in_items("  DFT-1001  |  Some reason  ")
        self.assertEqual(items[0]["item_id"], "DFT-1001")
        self.assertEqual(items[0]["relevance_summary"], "Some reason")

    def test_pipe_in_summary(self):
        """Split on first pipe only — summary can contain pipes."""
        items, errors = parse_cite_in_items("DFT-1001 | Reason | with extra pipe")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["relevance_summary"], "Reason | with extra pipe")

    def test_mixed_valid_and_invalid(self):
        raw = "DFT-1001 | Good one\nBAD-ID | Nope\nDFW-1002 | Also good"
        items, errors = parse_cite_in_items(raw)
        self.assertEqual(len(items), 2)
        self.assertEqual(len(errors), 1)

    def test_five_digit_id(self):
        items, errors = parse_cite_in_items("DFT-10001 | Reason")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["item_id"], "DFT-10001")

    def test_three_digit_id_rejected(self):
        items, errors = parse_cite_in_items("DFT-100 | Reason")
        self.assertEqual(items, [])
        self.assertEqual(len(errors), 1)


class TestValidateCiteItemsExist(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        for subdir in ("techniques", "weaknesses", "mitigations"):
            os.makedirs(os.path.join(self.tmpdir, "data", subdir))

    def _create_item(self, subdir, item_id):
        filepath = os.path.join(self.tmpdir, "data", subdir, f"{item_id}.json")
        with open(filepath, 'w') as f:
            json.dump({"id": item_id, "references": []}, f)

    def test_existing_technique(self):
        self._create_item("techniques", "DFT-1001")
        cite_items = [{"item_id": "DFT-1001", "relevance_summary": "Test"}]
        valid, warnings = validate_cite_items_exist(cite_items, self.tmpdir)
        self.assertEqual(len(valid), 1)
        self.assertEqual(warnings, [])

    def test_existing_weakness(self):
        self._create_item("weaknesses", "DFW-1001")
        cite_items = [{"item_id": "DFW-1001", "relevance_summary": "Test"}]
        valid, warnings = validate_cite_items_exist(cite_items, self.tmpdir)
        self.assertEqual(len(valid), 1)

    def test_existing_mitigation(self):
        self._create_item("mitigations", "DFM-1001")
        cite_items = [{"item_id": "DFM-1001", "relevance_summary": "Test"}]
        valid, warnings = validate_cite_items_exist(cite_items, self.tmpdir)
        self.assertEqual(len(valid), 1)

    def test_missing_item(self):
        cite_items = [{"item_id": "DFT-9999", "relevance_summary": "Test"}]
        valid, warnings = validate_cite_items_exist(cite_items, self.tmpdir)
        self.assertEqual(valid, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("not found", warnings[0])

    def test_mix_of_valid_and_invalid(self):
        self._create_item("techniques", "DFT-1001")
        cite_items = [
            {"item_id": "DFT-1001", "relevance_summary": "Valid"},
            {"item_id": "DFT-9999", "relevance_summary": "Invalid"},
        ]
        valid, warnings = validate_cite_items_exist(cite_items, self.tmpdir)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(warnings), 1)


class TestBuildCommentCiteInItems(unittest.TestCase):

    def _project_root(self):
        return os.path.join(os.path.dirname(__file__), '..')

    def test_cite_section_rendered_when_items_present(self):
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
            "Cite in items": "DFT-1001 | Reason for citing",
        }
        comment = build_comment(fields, self._project_root())
        self.assertIn("<!-- CITE_IN_ITEMS -->", comment)
        self.assertIn("### Cite in items", comment)
        self.assertIn("DFT-1001", comment)
        self.assertIn("Reason for citing", comment)
        # Should contain JSON block
        self.assertIn("```json", comment)

    def test_cite_section_omitted_when_empty(self):
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
            "Cite in items": "",
        }
        comment = build_comment(fields, self._project_root())
        self.assertNotIn("<!-- CITE_IN_ITEMS -->", comment)
        self.assertNotIn("### Cite in items", comment)

    def test_cite_section_omitted_when_no_response(self):
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
            "Cite in items": "_No response_",
        }
        comment = build_comment(fields, self._project_root())
        self.assertNotIn("<!-- CITE_IN_ITEMS -->", comment)

    def test_cite_section_omitted_when_no_field(self):
        """Backward compat: old issues without the field."""
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
        }
        comment = build_comment(fields, self._project_root())
        self.assertNotIn("<!-- CITE_IN_ITEMS -->", comment)

    def test_warnings_for_missing_items(self):
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
            "Cite in items": "DFT-9999 | Nonexistent item",
        }
        comment = build_comment(fields, self._project_root())
        self.assertIn("<!-- CITE_IN_ITEMS -->", comment)
        self.assertIn("Not found", comment)
        self.assertIn("Item warnings", comment)

    def test_no_cite_section_for_existing_match(self):
        """When the reference matches an existing citation, no cite section."""
        fields = {
            "Citation text": "DFCite-1003",
            "BibTeX entry": "_No response_",
            "Cite in items": "DFT-1001 | Should not appear",
        }
        comment = build_comment(fields, self._project_root())
        self.assertNotIn("<!-- CITE_IN_ITEMS -->", comment)

    def test_parse_errors_shown(self):
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
            "Cite in items": "BAD-ID | No good",
        }
        comment = build_comment(fields, self._project_root())
        self.assertIn("<!-- CITE_IN_ITEMS -->", comment)
        self.assertIn("Warnings", comment)
        self.assertIn("Invalid item ID format", comment)

    def test_json_block_parseable(self):
        """The JSON block in the comment should be valid and parseable."""
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
            "Cite in items": "DFT-1001 | Reason one\nDFW-1001 | Reason two",
        }
        comment = build_comment(fields, self._project_root())

        # Extract the JSON block
        import re
        match = re.search(r'```json\s*\n(.*?)\n```', comment, re.DOTALL)
        self.assertIsNotNone(match, "JSON block should be present")
        data = json.loads(match.group(1))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["item_id"], "DFT-1001")


if __name__ == "__main__":
    unittest.main()
