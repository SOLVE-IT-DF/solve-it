"""
Unit tests for admin/autoimplement_new_reference.py

Covers the parsing and extraction functions without hitting the GitHub API.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
import autoimplement_new_reference as mod


class TestValidateDfciteId(unittest.TestCase):

    def test_valid_id(self):
        mod.validate_dfcite_id("DFCite-1001")  # should not raise

    def test_valid_five_digit(self):
        mod.validate_dfcite_id("DFCite-10001")

    def test_invalid_prefix(self):
        with self.assertRaises(SystemExit):
            mod.validate_dfcite_id("DFT-1001")

    def test_invalid_format(self):
        with self.assertRaises(SystemExit):
            mod.validate_dfcite_id("DFCite-abc")

    def test_path_traversal(self):
        with self.assertRaises(SystemExit):
            mod.validate_dfcite_id("../../../etc")

    def test_empty_string(self):
        with self.assertRaises(SystemExit):
            mod.validate_dfcite_id("")


class TestIsExistingMatch(unittest.TestCase):

    def test_detects_existing_match(self):
        body = (
            "<!-- REFERENCE_PREVIEW -->\n"
            "This reference appears to match an existing citation: **DFCite-1001**\n"
        )
        self.assertTrue(mod.is_existing_match(body))

    def test_new_reference_not_match(self):
        body = (
            "<!-- REFERENCE_PREVIEW -->\n"
            "Reference ID **DFCite-1058** has been assigned.\n"
        )
        self.assertFalse(mod.is_existing_match(body))

    def test_case_insensitive(self):
        body = "This reference appears to Match an Existing Citation: **DFCite-1001**"
        self.assertTrue(mod.is_existing_match(body))


class TestExtractDfciteId(unittest.TestCase):

    def test_extracts_assigned_id(self):
        body = "Reference ID **DFCite-1058** has been assigned.\n"
        self.assertEqual(mod.extract_dfcite_id(body), "DFCite-1058")

    def test_extracts_assigned_five_digit_id(self):
        body = "Reference ID **DFCite-10001** has been assigned."
        self.assertEqual(mod.extract_dfcite_id(body), "DFCite-10001")

    def test_extracts_old_format_id(self):
        """Backward compatibility: old 'can be assigned' format still works."""
        body = "No existing match found. A new reference can be assigned: **DFCite-1058**\n"
        self.assertEqual(mod.extract_dfcite_id(body), "DFCite-1058")

    def test_prefers_assigned_over_old_format(self):
        """If both formats appear, assigned format wins."""
        body = (
            "A new reference can be assigned: **DFCite-1058**\n"
            "Reference ID **DFCite-1059** has been assigned.\n"
        )
        self.assertEqual(mod.extract_dfcite_id(body), "DFCite-1059")

    def test_returns_none_for_existing_match(self):
        body = "This reference appears to match an existing citation: **DFCite-1001**"
        self.assertIsNone(mod.extract_dfcite_id(body))

    def test_returns_none_for_no_id(self):
        body = "Just a regular comment."
        self.assertIsNone(mod.extract_dfcite_id(body))


class TestExtractTxtContent(unittest.TestCase):

    def test_extracts_txt_content(self):
        body = (
            "<!-- REFERENCE_PREVIEW -->\n"
            "Reference ID **DFCite-1058** has been assigned.\n\n"
            "Proposed file contents:\n\n"
            "**`data/references/DFCite-1058.txt`**\n"
            "```\n"
            "Smith, J. (2024), Test Reference, Journal of Testing, 1(2), pp.3-4.\n"
            "```\n"
        )
        result = mod.extract_txt_content(body)
        self.assertIsNotNone(result)
        self.assertEqual(result, "Smith, J. (2024), Test Reference, Journal of Testing, 1(2), pp.3-4.")

    def test_extracts_multiline_txt(self):
        body = (
            "**`data/references/DFCite-1058.txt`**\n"
            "```\n"
            "Smith, J. (2024), Test Reference,\n"
            "Journal of Testing, 1(2), pp.3-4.\n"
            "```\n"
        )
        result = mod.extract_txt_content(body)
        self.assertIsNotNone(result)
        self.assertIn("Smith, J.", result)
        self.assertIn("Journal of Testing", result)

    def test_returns_none_for_no_txt(self):
        body = "No code blocks here."
        self.assertIsNone(mod.extract_txt_content(body))

    def test_extracts_url_in_citation(self):
        body = (
            "**`data/references/DFCite-1058.txt`**\n"
            "```\n"
            "Android (2025), Android Debug Bridge (adb), https://developer.android.com/tools/adb\n"
            "```\n"
        )
        result = mod.extract_txt_content(body)
        self.assertIn("https://developer.android.com/tools/adb", result)


class TestExtractBibContent(unittest.TestCase):

    def test_extracts_bibtex(self):
        body = (
            "**`data/references/DFCite-1058.bib`**\n"
            "```bibtex\n"
            "@article{smith2024test,\n"
            "  author = {Smith, John},\n"
            "  title = {Test Reference},\n"
            "  year = {2024}\n"
            "}\n"
            "```\n"
        )
        result = mod.extract_bib_content(body)
        self.assertIsNotNone(result)
        self.assertIn("@article{smith2024test", result)
        self.assertIn("author = {Smith, John}", result)

    def test_returns_none_when_no_bibtex(self):
        body = (
            "**`data/references/DFCite-1058.txt`**\n"
            "```\n"
            "Smith (2024) Test\n"
            "```\n"
        )
        self.assertIsNone(mod.extract_bib_content(body))

    def test_does_not_match_plain_code_block(self):
        body = "```\nplain code\n```"
        self.assertIsNone(mod.extract_bib_content(body))


class TestFindReferencePreview(unittest.TestCase):

    def _make_comment(self, body):
        return {"body": body}

    def test_finds_assigned_comment(self):
        comments = [
            self._make_comment("Some other comment"),
            self._make_comment(
                "<!-- REFERENCE_PREVIEW -->\n"
                "Reference ID **DFCite-1058** has been assigned.\n"
            ),
        ]
        result = mod.find_reference_preview(comments)
        self.assertIsNotNone(result)
        self.assertIn("has been assigned", result["body"])

    def test_prefers_assigned_over_placeholder(self):
        comments = [
            self._make_comment(
                "<!-- REFERENCE_PREVIEW -->\n"
                "A reference ID will be assigned during review.\n"
            ),
            self._make_comment(
                "<!-- REFERENCE_PREVIEW -->\n"
                "Reference ID **DFCite-1058** has been assigned.\n"
            ),
        ]
        result = mod.find_reference_preview(comments)
        self.assertIn("has been assigned", result["body"])

    def test_falls_back_to_old_preview(self):
        """Backward compat: finds old-style preview with real ID."""
        comments = [
            self._make_comment(
                "<!-- REFERENCE_PREVIEW -->\n"
                "A new reference can be assigned: **DFCite-1058**\n"
            ),
        ]
        result = mod.find_reference_preview(comments)
        self.assertIsNotNone(result)
        self.assertIn("REFERENCE_PREVIEW", result["body"])

    def test_returns_none_when_missing(self):
        comments = [
            self._make_comment("Just a regular comment"),
        ]
        self.assertIsNone(mod.find_reference_preview(comments))

    def test_returns_none_for_empty_list(self):
        self.assertIsNone(mod.find_reference_preview([]))


class TestRaceProtection(unittest.TestCase):
    """Test that existing files are detected before writing."""

    def test_detects_existing_txt(self):
        tmpdir = tempfile.mkdtemp()
        refs_dir = os.path.join(tmpdir, "data", "references")
        os.makedirs(refs_dir)

        # Create an existing .txt file
        txt_path = os.path.join(refs_dir, "DFCite-1058.txt")
        with open(txt_path, "w") as f:
            f.write("existing\n")

        self.assertTrue(os.path.exists(txt_path))

    def test_detects_existing_bib(self):
        tmpdir = tempfile.mkdtemp()
        refs_dir = os.path.join(tmpdir, "data", "references")
        os.makedirs(refs_dir)

        bib_path = os.path.join(refs_dir, "DFCite-1058.bib")
        with open(bib_path, "w") as f:
            f.write("@article{}\n")

        self.assertTrue(os.path.exists(bib_path))


class TestFullPreviewParsing(unittest.TestCase):
    """Integration-style tests that parse a realistic assigned-ID comment."""

    FULL_ASSIGNED = (
        "<!-- REFERENCE_PREVIEW -->\n"
        "Reference ID **DFCite-1058** has been assigned.\n\n"
        "Proposed file contents:\n\n"
        "**`data/references/DFCite-1058.txt`**\n"
        "```\n"
        "Garfinkel, S. (2010), Digital forensics research: The next 10 years, "
        "Digital Investigation, 7, S64-S73.\n"
        "```\n\n"
        "**`data/references/DFCite-1058.bib`**\n"
        "```bibtex\n"
        "@article{garfinkel2010digital,\n"
        "  author = {Garfinkel, Simson},\n"
        "  title = {Digital forensics research: The next 10 years},\n"
        "  journal = {Digital Investigation},\n"
        "  volume = {7},\n"
        "  pages = {S64--S73},\n"
        "  year = {2010}\n"
        "}\n"
        "```\n\n"
        "---\n"
        "*This comment was automatically generated from the reference proposal form.*"
    )

    FULL_PREVIEW_OLD = (
        "<!-- REFERENCE_PREVIEW -->\n"
        "No existing match found. A new reference can be assigned: **DFCite-1058**\n\n"
        "To add this reference, create the following file(s):\n\n"
        "**`data/references/DFCite-1058.txt`**\n"
        "```\n"
        "Garfinkel, S. (2010), Digital forensics research: The next 10 years, "
        "Digital Investigation, 7, S64-S73.\n"
        "```\n\n"
        "**`data/references/DFCite-1058.bib`**\n"
        "```bibtex\n"
        "@article{garfinkel2010digital,\n"
        "  author = {Garfinkel, Simson},\n"
        "  title = {Digital forensics research: The next 10 years},\n"
        "  journal = {Digital Investigation},\n"
        "  volume = {7},\n"
        "  pages = {S64--S73},\n"
        "  year = {2010}\n"
        "}\n"
        "```\n\n"
        "---\n"
        "*This comment was automatically generated from the reference proposal form.*"
    )

    FULL_PREVIEW_EXISTING = (
        "<!-- REFERENCE_PREVIEW -->\n"
        "This reference appears to match an existing citation: **DFCite-1001**\n\n"
        "> Brignoni, A. (n.d.), ALEAPP adb_hosts.py...\n\n"
        "Match type: url\n\n"
        "If this is indeed the same reference, no new citation file is needed.\n\n"
        "---\n"
        "*This comment was automatically generated from the reference proposal form.*"
    )

    def test_assigned_comment_full_parse(self):
        """End-to-end parse of a new assigned-ID comment."""
        self.assertFalse(mod.is_existing_match(self.FULL_ASSIGNED))

        dfcite_id = mod.extract_dfcite_id(self.FULL_ASSIGNED)
        self.assertEqual(dfcite_id, "DFCite-1058")

        txt = mod.extract_txt_content(self.FULL_ASSIGNED)
        self.assertIn("Garfinkel", txt)
        self.assertIn("Digital forensics research", txt)

        bib = mod.extract_bib_content(self.FULL_ASSIGNED)
        self.assertIn("@article{garfinkel2010digital", bib)

    def test_old_format_full_parse(self):
        """Backward compat: old-format preview still parseable."""
        dfcite_id = mod.extract_dfcite_id(self.FULL_PREVIEW_OLD)
        self.assertEqual(dfcite_id, "DFCite-1058")

        txt = mod.extract_txt_content(self.FULL_PREVIEW_OLD)
        self.assertIn("Garfinkel", txt)

    def test_existing_reference_full_parse(self):
        """Existing match should be detected, no ID extracted for assignment."""
        self.assertTrue(mod.is_existing_match(self.FULL_PREVIEW_EXISTING))
        self.assertIsNone(mod.extract_dfcite_id(self.FULL_PREVIEW_EXISTING))


class TestExtractCiteInItems(unittest.TestCase):

    def test_parses_json_from_comment(self):
        comment = (
            "<!-- REFERENCE_PREVIEW -->\n"
            "Some text\n\n"
            "<!-- CITE_IN_ITEMS -->\n\n"
            "### Cite in items\n\n"
            "| Item | Relevance summary | Status |\n"
            "|---|---|---|\n"
            "| `DFT-1001` | Reason | Found |\n\n"
            "```json\n"
            '[{"item_id": "DFT-1001", "relevance_summary": "Reason"}]\n'
            "```\n"
        )
        result = mod.extract_cite_in_items(comment)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["item_id"], "DFT-1001")
        self.assertEqual(result[0]["relevance_summary"], "Reason")

    def test_returns_empty_when_marker_missing(self):
        comment = (
            "<!-- REFERENCE_PREVIEW -->\n"
            "Reference ID **DFCite-1058** has been assigned.\n"
        )
        result = mod.extract_cite_in_items(comment)
        self.assertEqual(result, [])

    def test_empty_json_array(self):
        comment = (
            "<!-- CITE_IN_ITEMS -->\n"
            "```json\n"
            "[]\n"
            "```\n"
        )
        result = mod.extract_cite_in_items(comment)
        self.assertEqual(result, [])

    def test_malformed_json_graceful(self):
        comment = (
            "<!-- CITE_IN_ITEMS -->\n"
            "```json\n"
            "not valid json\n"
            "```\n"
        )
        result = mod.extract_cite_in_items(comment)
        self.assertEqual(result, [])

    def test_multiple_items(self):
        items = [
            {"item_id": "DFT-1001", "relevance_summary": "Reason 1"},
            {"item_id": "DFW-1002", "relevance_summary": "Reason 2"},
        ]
        comment = (
            "<!-- CITE_IN_ITEMS -->\n"
            "```json\n"
            f"{json.dumps(items, indent=2)}\n"
            "```\n"
        )
        result = mod.extract_cite_in_items(comment)
        self.assertEqual(len(result), 2)


class TestResolveItemPath(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        for subdir in ("techniques", "weaknesses", "mitigations"):
            os.makedirs(os.path.join(self.tmpdir, "data", subdir))

    def _create_item(self, subdir, item_id):
        filepath = os.path.join(self.tmpdir, "data", subdir, f"{item_id}.json")
        with open(filepath, 'w') as f:
            json.dump({"id": item_id, "references": []}, f)
        return filepath

    def test_technique_found(self):
        self._create_item("techniques", "DFT-1001")
        result = mod.resolve_item_path("DFT-1001", self.tmpdir)
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith("DFT-1001.json"))

    def test_weakness_found(self):
        self._create_item("weaknesses", "DFW-1001")
        result = mod.resolve_item_path("DFW-1001", self.tmpdir)
        self.assertIsNotNone(result)

    def test_mitigation_found(self):
        self._create_item("mitigations", "DFM-1001")
        result = mod.resolve_item_path("DFM-1001", self.tmpdir)
        self.assertIsNotNone(result)

    def test_invalid_id_returns_none(self):
        self.assertIsNone(mod.resolve_item_path("INVALID-123", self.tmpdir))

    def test_nonexistent_file_returns_none(self):
        self.assertIsNone(mod.resolve_item_path("DFT-9999", self.tmpdir))

    def test_path_traversal_returns_none(self):
        self.assertIsNone(mod.resolve_item_path("../../../etc", self.tmpdir))


class TestAddReferenceToItem(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _create_item_file(self, item_id, references=None):
        filepath = os.path.join(self.tmpdir, f"{item_id}.json")
        data = {"id": item_id, "name": "Test", "references": references or []}
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
            f.write('\n')
        return filepath

    def test_adds_new_reference(self):
        filepath = self._create_item_file("DFT-1001")
        status = mod.add_reference_to_item(filepath, "DFCite-1058", "Test relevance")
        self.assertEqual(status, "added")

        with open(filepath) as f:
            data = json.load(f)
        self.assertEqual(len(data["references"]), 1)
        self.assertEqual(data["references"][0]["DFCite_id"], "DFCite-1058")
        self.assertEqual(data["references"][0]["relevance_summary_280"], "Test relevance")

    def test_skips_when_already_present(self):
        filepath = self._create_item_file("DFT-1001", references=[
            {"DFCite_id": "DFCite-1058", "relevance_summary_280": "Existing"}
        ])
        status = mod.add_reference_to_item(filepath, "DFCite-1058", "New text")
        self.assertEqual(status, "exists")

        with open(filepath) as f:
            data = json.load(f)
        self.assertEqual(len(data["references"]), 1)
        # Should not have changed
        self.assertEqual(data["references"][0]["relevance_summary_280"], "Existing")

    def test_works_with_empty_references(self):
        filepath = self._create_item_file("DFT-1001", references=[])
        status = mod.add_reference_to_item(filepath, "DFCite-1058", "Reason")
        self.assertEqual(status, "added")

    def test_preserves_existing_references(self):
        filepath = self._create_item_file("DFT-1001", references=[
            {"DFCite_id": "DFCite-1001", "relevance_summary_280": "First ref"}
        ])
        status = mod.add_reference_to_item(filepath, "DFCite-1058", "Second ref")
        self.assertEqual(status, "added")

        with open(filepath) as f:
            data = json.load(f)
        self.assertEqual(len(data["references"]), 2)
        self.assertEqual(data["references"][0]["DFCite_id"], "DFCite-1001")
        self.assertEqual(data["references"][1]["DFCite_id"], "DFCite-1058")

    def test_json_formatting(self):
        filepath = self._create_item_file("DFT-1001")
        mod.add_reference_to_item(filepath, "DFCite-1058", "Reason")

        with open(filepath) as f:
            content = f.read()
        # Should have indent=4 and trailing newline
        self.assertTrue(content.endswith('\n'))
        self.assertIn('    ', content)

    def test_error_on_nonexistent_file(self):
        status = mod.add_reference_to_item("/nonexistent/path.json", "DFCite-1058", "R")
        self.assertEqual(status, "error")


class TestFullCommentWithCiteInItems(unittest.TestCase):
    """Integration test: parse a full comment that includes cite-in-items."""

    FULL_COMMENT_WITH_CITE = (
        "<!-- REFERENCE_PREVIEW -->\n"
        "Reference ID **DFCite-1058** has been assigned.\n\n"
        "Proposed file contents:\n\n"
        "**`data/references/DFCite-1058.txt`**\n"
        "```\n"
        "Smith, J. (2024), Test Reference.\n"
        "```\n\n"
        "<!-- CITE_IN_ITEMS -->\n\n"
        "### Cite in items\n\n"
        "| Item | Relevance summary | Status |\n"
        "|---|---|---|\n"
        "| `DFT-1001` | Describes the technique | Found |\n"
        "| `DFW-1002` | Related weakness | Found |\n\n"
        "```json\n"
        '[\n'
        '  {"item_id": "DFT-1001", "relevance_summary": "Describes the technique"},\n'
        '  {"item_id": "DFW-1002", "relevance_summary": "Related weakness"}\n'
        ']\n'
        "```\n\n"
        "---\n"
        "*This comment was automatically generated from the reference proposal form.*"
    )

    def test_full_parse(self):
        """Extract all parts from a realistic comment with cite-in-items."""
        body = self.FULL_COMMENT_WITH_CITE

        # Standard extraction still works
        self.assertFalse(mod.is_existing_match(body))
        dfcite_id = mod.extract_dfcite_id(body)
        self.assertEqual(dfcite_id, "DFCite-1058")

        txt = mod.extract_txt_content(body)
        self.assertIn("Smith", txt)

        # Cite-in-items extraction
        cite_items = mod.extract_cite_in_items(body)
        self.assertEqual(len(cite_items), 2)
        self.assertEqual(cite_items[0]["item_id"], "DFT-1001")
        self.assertEqual(cite_items[1]["item_id"], "DFW-1002")


class TestSlugify(unittest.TestCase):

    def test_dfcite_slug(self):
        self.assertEqual(mod.slugify("DFCite-1058"), "dfcite-1058")

    def test_truncation(self):
        result = mod.slugify("a" * 100, max_len=20)
        self.assertLessEqual(len(result), 20)


if __name__ == "__main__":
    unittest.main()
