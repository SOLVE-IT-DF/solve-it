"""Tests for solve_it_library/reference_matching.py"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library.reference_matching import (
    _extract_dois,
    _extract_urls,
    match_reference,
)


class TestExtractDois(unittest.TestCase):
    """Tests for _extract_dois helper."""

    def test_doi_org_url(self):
        text = "Available at https://doi.org/10.1016/j.fsidi.2020.300909"
        result = _extract_dois(text)
        self.assertEqual(result, {"10.1016/j.fsidi.2020.300909"})

    def test_doi_org_https(self):
        text = "https://doi.org/10.17632/abcdef1234.1"
        result = _extract_dois(text)
        self.assertEqual(result, {"10.17632/abcdef1234.1"})

    def test_doi_prefix_with_space(self):
        text = "doi: 10.17632/abcdef1234.1"
        result = _extract_dois(text)
        self.assertEqual(result, {"10.17632/abcdef1234.1"})

    def test_doi_prefix_no_space(self):
        text = "doi:10.1234/foo"
        result = _extract_dois(text)
        self.assertEqual(result, {"10.1234/foo"})

    def test_bare_doi(self):
        text = "Some paper, 10.1016/j.diin.2019.04.008, published 2019"
        result = _extract_dois(text)
        self.assertEqual(result, {"10.1016/j.diin.2019.04.008"})

    def test_no_doi(self):
        text = "A paper with no DOI at all"
        result = _extract_dois(text)
        self.assertEqual(result, set())

    def test_multiple_dois(self):
        text = "See 10.1016/j.fsidi.2020.300909 and doi: 10.17632/xyz.1"
        result = _extract_dois(text)
        self.assertEqual(result, {"10.1016/j.fsidi.2020.300909", "10.17632/xyz.1"})

    def test_case_insensitive_prefix(self):
        text = "DOI: 10.1234/Test.Case"
        result = _extract_dois(text)
        self.assertEqual(result, {"10.1234/test.case"})

    def test_trailing_period_stripped(self):
        text = "See doi: 10.1234/foo."
        result = _extract_dois(text)
        self.assertEqual(result, {"10.1234/foo"})


class TestExtractUrls(unittest.TestCase):
    """Tests for _extract_urls helper."""

    def test_basic_url(self):
        text = "See https://example.com/page for details"
        self.assertEqual(_extract_urls(text), {"https://example.com/page"})

    def test_multiple_urls(self):
        text = "http://a.com and https://b.com/path"
        self.assertEqual(_extract_urls(text), {"http://a.com", "https://b.com/path"})

    def test_no_urls(self):
        self.assertEqual(_extract_urls("no urls here"), set())


class TestMatchReference(unittest.TestCase):
    """Tests for match_reference."""

    CORPUS = {
        "DFCite-1001": "Smith, J. (2020). A study. https://example.com/paper",
        "DFCite-1002": "Jones, A. (2021). Another study. doi: 10.1016/j.fsidi.2021.123456",
        "DFCite-1003": "Brown, B. (2019). Third study on forensics, with a very long title for prefix matching purposes.",
    }

    # Direct ID match
    def test_direct_id_found(self):
        result = match_reference("DFCite-1001", self.CORPUS)
        self.assertEqual(result, ("DFCite-1001", "direct_id"))

    def test_direct_id_not_found(self):
        result = match_reference("DFCite-9999", self.CORPUS)
        self.assertIsNone(result)

    # URL overlap match
    def test_url_overlap(self):
        text = "Smith (2020) A study. https://example.com/paper"
        result = match_reference(text, self.CORPUS)
        self.assertEqual(result, ("DFCite-1001", "url"))

    # DOI overlap match
    def test_doi_overlap_bare(self):
        text = "Some citation referencing 10.1016/j.fsidi.2021.123456"
        result = match_reference(text, self.CORPUS)
        self.assertEqual(result, ("DFCite-1002", "doi"))

    def test_doi_overlap_url_form(self):
        text = "See https://doi.org/10.1016/j.fsidi.2021.123456"
        result = match_reference(text, self.CORPUS)
        # Could match as URL (doi.org URL not in corpus) or DOI — DOI expected
        # since corpus has "doi: 10.1016/..." not "https://doi.org/..."
        self.assertEqual(result, ("DFCite-1002", "doi"))

    def test_doi_overlap_prefix_form(self):
        text = "doi:10.1016/j.fsidi.2021.123456"
        result = match_reference(text, self.CORPUS)
        self.assertEqual(result, ("DFCite-1002", "doi"))

    # Prefix match
    def test_prefix_match(self):
        text = "Brown, B. (2019). Third study on forensics, with a very long title for prefix matching purposes. Extra text."
        result = match_reference(text, self.CORPUS)
        self.assertEqual(result, ("DFCite-1003", "prefix"))

    # No match
    def test_no_match(self):
        text = "A completely unrelated citation that matches nothing in the corpus"
        result = match_reference(text, self.CORPUS)
        self.assertIsNone(result)

    # Empty input
    def test_empty_input(self):
        self.assertIsNone(match_reference("", self.CORPUS))

    def test_whitespace_input(self):
        self.assertIsNone(match_reference("   ", self.CORPUS))

    # Priority: direct ID > URL > DOI > prefix
    def test_url_beats_doi(self):
        """URL match should take priority over DOI match."""
        corpus = {
            "DFCite-2001": "Paper at https://example.com/p1 with doi: 10.1234/same",
        }
        text = "Found at https://example.com/p1 doi: 10.1234/same"
        result = match_reference(text, corpus)
        self.assertEqual(result[1], "url")

    def test_doi_beats_prefix(self):
        """DOI match should take priority over prefix match."""
        corpus = {
            "DFCite-3001": "Exact prefix text here xxxxxxxxx doi: 10.9999/unique",
        }
        text = "Exact prefix text here xxxxxxxxx 10.9999/unique"
        result = match_reference(text, corpus)
        self.assertEqual(result[1], "doi")


if __name__ == '__main__':
    unittest.main()
