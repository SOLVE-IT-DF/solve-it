"""Tests for inline [DFCite-xxxx] citation detection, including list fields."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library.citation_utils import find_inline_citations


class TestFindInlineCitations(unittest.TestCase):

    def test_finds_single_citation(self):
        text = "As described in [DFCite-1115]."
        self.assertEqual(find_inline_citations(text), ["DFCite-1115"])

    def test_finds_multiple_citations(self):
        text = "See [DFCite-1001] and [DFCite-1042] for details."
        self.assertEqual(find_inline_citations(text), ["DFCite-1001", "DFCite-1042"])

    def test_no_citations(self):
        text = "No citations here."
        self.assertEqual(find_inline_citations(text), [])

    def test_empty_string(self):
        self.assertEqual(find_inline_citations(""), [])


class TestInlineCitationsInListFields(unittest.TestCase):
    """Tests that the list-to-string joining logic in validate_kb works for
    fields like 'examples' which are stored as lists of strings."""

    def _extract_from_field(self, value):
        """Mimics the logic in validate_kb phase2_cross_references."""
        value = value if value else ""
        text = "\n".join(value) if isinstance(value, list) else value
        return find_inline_citations(text)

    def test_list_with_citation(self):
        examples = ["Tool A [DFCite-1001]", "Tool B"]
        self.assertEqual(self._extract_from_field(examples), ["DFCite-1001"])

    def test_list_with_multiple_citations(self):
        examples = ["Tool A [DFCite-1001]", "Tool B [DFCite-1002]"]
        self.assertEqual(self._extract_from_field(examples), ["DFCite-1001", "DFCite-1002"])

    def test_list_without_citations(self):
        examples = ["Tool A", "Tool B"]
        self.assertEqual(self._extract_from_field(examples), [])

    def test_empty_list(self):
        self.assertEqual(self._extract_from_field([]), [])

    def test_none_value(self):
        self.assertEqual(self._extract_from_field(None), [])

    def test_string_still_works(self):
        text = "Described in [DFCite-1050]."
        self.assertEqual(self._extract_from_field(text), ["DFCite-1050"])


if __name__ == '__main__':
    unittest.main()
