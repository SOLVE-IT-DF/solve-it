"""
Tests for admin/issue_parsers/parse_update_reference_issue.py.

Covers:
- DFCite ID validation
- load_raw_file helper
- build_comment with real KB (integration)
- Comment structure: marker, current/proposed sections, summary
- No-change detection
- Cite-in-items handling: new items, already-cited dedup, errors
- Non-existent DFCite error handling
- Data block JSON validity
"""

import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parse_update_reference_issue import (
    build_comment,
    DFCITE_RE,
    load_raw_file,
)


def _project_root():
    return os.path.join(os.path.dirname(__file__), '..')


class TestDfciteIdRegex(unittest.TestCase):

    def test_valid_four_digit(self):
        self.assertIsNotNone(DFCITE_RE.match("DFCite-1001"))

    def test_valid_five_digit(self):
        self.assertIsNotNone(DFCITE_RE.match("DFCite-10001"))

    def test_valid_six_digit(self):
        self.assertIsNotNone(DFCITE_RE.match("DFCite-100001"))

    def test_invalid_three_digit(self):
        self.assertIsNone(DFCITE_RE.match("DFCite-100"))

    def test_invalid_prefix(self):
        self.assertIsNone(DFCITE_RE.match("DFT-1001"))

    def test_invalid_no_dash(self):
        self.assertIsNone(DFCITE_RE.match("DFCite1001"))

    def test_invalid_empty(self):
        self.assertIsNone(DFCITE_RE.match(""))

    def test_invalid_letters_after_dash(self):
        self.assertIsNone(DFCITE_RE.match("DFCite-abcd"))


class TestLoadRawFile(unittest.TestCase):

    def test_existing_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("  Hello world  \n")
            path = f.name
        try:
            self.assertEqual(load_raw_file(path), "Hello world")
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        self.assertIsNone(load_raw_file("/nonexistent/path/file.txt"))

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")
            path = f.name
        try:
            self.assertEqual(load_raw_file(path), "")
        finally:
            os.unlink(path)


class TestBuildCommentInvalidId(unittest.TestCase):

    def test_invalid_id_raises(self):
        fields = {"DFCite ID": "INVALID"}
        with self.assertRaises(ValueError) as ctx:
            build_comment(fields, _project_root())
        self.assertIn("Invalid DFCite ID", str(ctx.exception))

    def test_empty_id_raises(self):
        fields = {"DFCite ID": ""}
        with self.assertRaises(ValueError):
            build_comment(fields, _project_root())

    def test_technique_id_raises(self):
        fields = {"DFCite ID": "DFT-1001"}
        with self.assertRaises(ValueError):
            build_comment(fields, _project_root())


class TestBuildCommentNonexistent(unittest.TestCase):

    def test_nonexistent_dfcite(self):
        fields = {
            "DFCite ID": "DFCite-9999",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        comment, dfcite_id = build_comment(fields, _project_root())
        self.assertEqual(dfcite_id, "DFCite-9999")
        self.assertIn("**Error:**", comment)
        self.assertIn("was not found", comment)
        self.assertIn("DFCite-9999", comment)
        self.assertNotIn("<!-- REFERENCE_UPDATE_PREVIEW -->", comment)


class TestBuildCommentBasic(unittest.TestCase):
    """Integration tests against a real DFCite in the KB."""

    def _build(self, **overrides):
        fields = {
            "DFCite ID": "DFCite-1003",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        fields.update(overrides)
        return build_comment(fields, _project_root())

    def test_marker_present(self):
        comment, _ = self._build()
        self.assertIn("<!-- REFERENCE_UPDATE_PREVIEW -->", comment)

    def test_dfcite_id_in_header(self):
        comment, _ = self._build()
        self.assertIn("## Proposed update to DFCite-1003", comment)

    def test_current_text_shown(self):
        comment, _ = self._build()
        self.assertIn("### Current citation text", comment)
        # DFCite-1003 has a .txt file — should show its content
        self.assertIn("Android", comment)

    def test_current_bibtex_shown(self):
        comment, _ = self._build()
        self.assertIn("### Current BibTeX", comment)
        self.assertIn("```bibtex", comment)

    def test_no_changes_warning(self):
        comment, _ = self._build()
        self.assertIn(":warning: **No changes were proposed.**", comment)
        self.assertIn("No changes detected.", comment)

    def test_footer_present(self):
        comment, _ = self._build()
        self.assertIn("automatically generated from the update form", comment)


class TestBuildCommentTextChange(unittest.TestCase):

    def _build(self, **overrides):
        fields = {
            "DFCite ID": "DFCite-1003",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        fields.update(overrides)
        return build_comment(fields, _project_root())

    def test_proposed_text_shown(self):
        comment, _ = self._build(**{
            "New citation text": "New citation text here."
        })
        self.assertIn("### Proposed citation text", comment)
        self.assertIn("> New citation text here.", comment)
        # The "no change" message should not appear between the proposed text heading
        # and the proposed BibTeX heading
        txt_section = comment.split("### Proposed citation text")[1].split("### Proposed BibTeX")[0]
        self.assertNotIn("No change proposed", txt_section)

    def test_text_change_in_summary(self):
        comment, _ = self._build(**{
            "New citation text": "New citation text here."
        })
        self.assertIn("**Citation text**: changed", comment)

    def test_no_warning_when_text_changed(self):
        comment, _ = self._build(**{
            "New citation text": "New citation text here."
        })
        self.assertNotIn(":warning: **No changes were proposed.**", comment)

    def test_identical_text_flagged(self):
        """Submitting the same text as current should say no change."""
        # DFCite-1003.txt content
        current = "Android (2025), Android Debug Bridge (adb), https://developer.android.com/tools/adb"
        comment, _ = self._build(**{"New citation text": current})
        self.assertIn("*No change from current text.*", comment)


class TestBuildCommentBibtexChange(unittest.TestCase):

    def _build(self, **overrides):
        fields = {
            "DFCite ID": "DFCite-1003",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        fields.update(overrides)
        return build_comment(fields, _project_root())

    def test_proposed_bibtex_shown(self):
        comment, _ = self._build(**{
            "New BibTeX entry": "@article{test, title={Test}}"
        })
        self.assertIn("### Proposed BibTeX", comment)
        self.assertIn("@article{test", comment)

    def test_bibtex_change_in_summary(self):
        comment, _ = self._build(**{
            "New BibTeX entry": "@article{test, title={Test}}"
        })
        self.assertIn("**BibTeX**: changed", comment)

    def test_blank_bibtex_shows_no_change(self):
        comment, _ = self._build()
        # Should show "No change proposed" for BibTeX
        self.assertIn("*No change proposed (field left blank).*", comment)


class TestBuildCommentDataBlock(unittest.TestCase):

    def _build(self, **overrides):
        fields = {
            "DFCite ID": "DFCite-1003",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        fields.update(overrides)
        return build_comment(fields, _project_root())

    def _extract_data(self, comment):
        match = re.search(r'```json\s*\n(.*?)\n```', comment, re.DOTALL)
        self.assertIsNotNone(match, "JSON data block should be present")
        return json.loads(match.group(1))

    def test_data_block_valid_json(self):
        comment, _ = self._build()
        data = self._extract_data(comment)
        self.assertEqual(data["dfcite_id"], "DFCite-1003")

    def test_data_block_includes_new_txt(self):
        comment, _ = self._build(**{"New citation text": "Updated text."})
        data = self._extract_data(comment)
        self.assertEqual(data["new_txt"], "Updated text.")

    def test_data_block_includes_new_bib(self):
        comment, _ = self._build(**{
            "New BibTeX entry": "@misc{test, title={T}}"
        })
        data = self._extract_data(comment)
        self.assertEqual(data["new_bib"], "@misc{test, title={T}}")

    def test_data_block_omits_blank_fields(self):
        comment, _ = self._build()
        data = self._extract_data(comment)
        self.assertNotIn("new_txt", data)
        self.assertNotIn("new_bib", data)

    def test_data_block_includes_cite_items(self):
        comment, _ = self._build(**{
            "Cite in additional items": "DFT-1001 | Reason here"
        })
        data = self._extract_data(comment)
        self.assertIn("cite_in_items", data)
        self.assertEqual(len(data["cite_in_items"]), 1)
        self.assertEqual(data["cite_in_items"][0]["item_id"], "DFT-1001")

    def test_data_block_omits_already_cited(self):
        """Items already citing the DFCite should not appear in data block."""
        # DFCite-1003 is cited by DFM-1238 in the real KB
        comment, _ = self._build(**{
            "Cite in additional items": "DFM-1238 | Already cited"
        })
        data = self._extract_data(comment)
        self.assertNotIn("cite_in_items", data)


class TestBuildCommentCiteInItems(unittest.TestCase):

    def _build(self, **overrides):
        fields = {
            "DFCite ID": "DFCite-1003",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        fields.update(overrides)
        return build_comment(fields, _project_root())

    def test_cite_section_shown_when_items_present(self):
        comment, _ = self._build(**{
            "Cite in additional items": "DFT-1001 | Reason"
        })
        self.assertIn("### Cite in additional items", comment)

    def test_cite_section_hidden_when_blank(self):
        comment, _ = self._build()
        self.assertNotIn("### Cite in additional items", comment)

    def test_cite_section_hidden_when_no_response(self):
        comment, _ = self._build(**{
            "Cite in additional items": "_No response_"
        })
        self.assertNotIn("### Cite in additional items", comment)

    def test_new_cite_items_in_table(self):
        comment, _ = self._build(**{
            "Cite in additional items": "DFT-1001 | Triage tool"
        })
        self.assertIn("| `DFT-1001`", comment)
        self.assertIn("Triage tool", comment)

    def test_already_cited_with_new_relevance_flagged_as_update(self):
        """DFCite-1003 is cited by DFM-1238 with empty relevance — supplying
        a new relevance string should flag it as a relevance update."""
        comment, _ = self._build(**{
            "Cite in additional items": "DFM-1238 | Already cited"
        })
        self.assertIn("already cite", comment)
        self.assertIn("DFM-1238", comment)
        self.assertIn("relevance will be updated", comment)

    def test_already_cited_same_relevance_skipped(self):
        """When the supplied relevance matches the existing one, the item
        should be skipped with no change."""
        comment, _ = self._build(**{
            "Cite in additional items": "DFM-1238 | "
        })
        # Empty relevance matches existing empty — should be skipped
        self.assertNotIn("relevance will be updated", comment)
        self.assertNotIn("**Cite in items**: add to", comment)

    def test_already_cited_relevance_update_in_summary(self):
        """A relevance update should appear in the summary of changes."""
        comment, _ = self._build(**{
            "Cite in additional items": "DFM-1238 | Already cited"
        })
        self.assertIn("update relevance in 1 item(s)", comment)
        self.assertNotIn("**Cite in items**: add to", comment)

    def test_mix_new_and_already_cited(self):
        comment, _ = self._build(**{
            "Cite in additional items": "DFT-1001 | New one\nDFM-1238 | Existing"
        })
        self.assertIn("add to 1 new item(s)", comment)
        self.assertIn("relevance will be updated", comment)

    def test_invalid_cite_format_shows_warning(self):
        comment, _ = self._build(**{
            "Cite in additional items": "BAD-ID | Nope"
        })
        self.assertIn("### Cite in additional items", comment)
        self.assertIn("Warnings", comment)
        self.assertIn("Invalid item ID format", comment)

    def test_nonexistent_item_shows_warning(self):
        comment, _ = self._build(**{
            "Cite in additional items": "DFT-9999 | Ghost item"
        })
        self.assertIn("Not found", comment)

    def test_cite_changes_in_summary(self):
        comment, _ = self._build(**{
            "Cite in additional items": "DFT-1001 | New citation"
        })
        self.assertIn("**Cite in items**: add to 1 new item(s)", comment)


class TestBuildCommentCitedBy(unittest.TestCase):

    def _build(self, **overrides):
        fields = {
            "DFCite ID": "DFCite-1003",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        fields.update(overrides)
        return build_comment(fields, _project_root())

    def test_cited_by_section_present(self):
        """DFCite-1003 is cited by at least one item."""
        comment, _ = self._build()
        self.assertIn("### Currently cited by", comment)

    def test_cited_by_lists_item(self):
        comment, _ = self._build()
        self.assertIn("DFM-1238", comment)


class TestBuildCommentBibOnlyRef(unittest.TestCase):
    """Test with a DFCite that has only a .bib file (no .txt)."""

    def test_bib_only_ref(self):
        # DFCite-1001 has only a .bib file in the real KB
        bib_path = os.path.join(_project_root(), "data", "references", "DFCite-1001.bib")
        txt_path = os.path.join(_project_root(), "data", "references", "DFCite-1001.txt")
        if not os.path.exists(bib_path):
            self.skipTest("DFCite-1001.bib not present")
        if os.path.exists(txt_path):
            self.skipTest("DFCite-1001.txt exists — not a bib-only ref")

        fields = {
            "DFCite ID": "DFCite-1001",
            "New citation text": "_No response_",
            "New BibTeX entry": "_No response_",
            "Cite in additional items": "_No response_",
        }
        comment, _ = build_comment(fields, _project_root())
        self.assertIn("*(no .txt file)*", comment)
        self.assertIn("```bibtex", comment)


class TestBuildCommentBothChanges(unittest.TestCase):

    def test_both_text_and_bib_changed(self):
        fields = {
            "DFCite ID": "DFCite-1003",
            "New citation text": "New text here.",
            "New BibTeX entry": "@misc{new, title={New}}",
            "Cite in additional items": "_No response_",
        }
        comment, _ = build_comment(fields, _project_root())
        self.assertIn("**Citation text**: changed", comment)
        self.assertIn("**BibTeX**: changed", comment)
        self.assertNotIn(":warning: **No changes were proposed.**", comment)


if __name__ == '__main__':
    unittest.main()
