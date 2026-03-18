"""
Unit tests for admin/autoimplement_new_item.py

Covers the parsing and extraction functions without hitting the GitHub API.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
import autoimplement_new_item as mod


class TestValidateId(unittest.TestCase):
    """Test ID validation."""

    def test_valid_technique_id(self):
        mod.validate_id("DFT-1001")  # should not raise

    def test_valid_weakness_id(self):
        mod.validate_id("DFW-1234")

    def test_valid_mitigation_id(self):
        mod.validate_id("DFM-10001")  # 5-digit

    def test_invalid_prefix(self):
        with self.assertRaises(SystemExit):
            mod.validate_id("DFX-1001")

    def test_placeholder_rejected(self):
        with self.assertRaises(SystemExit):
            mod.validate_id("DFT-____")

    def test_path_traversal_rejected(self):
        with self.assertRaises(SystemExit):
            mod.validate_id("../../../etc/passwd")

    def test_empty_string_rejected(self):
        with self.assertRaises(SystemExit):
            mod.validate_id("")


class TestNormalizeId(unittest.TestCase):
    """Test old-format to new-format ID normalization."""

    def test_new_format_unchanged(self):
        self.assertEqual(mod.normalize_id("DFT-1001"), "DFT-1001")
        self.assertEqual(mod.normalize_id("DFW-1234"), "DFW-1234")
        self.assertEqual(mod.normalize_id("DFM-5678"), "DFM-5678")

    def test_old_technique(self):
        self.assertEqual(mod.normalize_id("T1234"), "DFT-1234")

    def test_old_weakness(self):
        self.assertEqual(mod.normalize_id("W1234"), "DFW-1234")

    def test_old_mitigation(self):
        self.assertEqual(mod.normalize_id("M1240"), "DFM-1240")

    def test_invalid_returns_none(self):
        self.assertIsNone(mod.normalize_id("X1234"))
        self.assertIsNone(mod.normalize_id("DFT-____"))
        self.assertIsNone(mod.normalize_id("../etc"))
        self.assertIsNone(mod.normalize_id(""))


class TestClassifyType(unittest.TestCase):
    """Test type classification from ID prefix."""

    def test_technique(self):
        self.assertEqual(mod.classify_type("DFT-1001"), "technique")

    def test_weakness(self):
        self.assertEqual(mod.classify_type("DFW-1001"), "weakness")

    def test_mitigation(self):
        self.assertEqual(mod.classify_type("DFM-1001"), "mitigation")

    def test_unknown_prefix(self):
        self.assertIsNone(mod.classify_type("DFX-1001"))


class TestExtractJsonBlock(unittest.TestCase):
    """Test JSON block extraction from comment bodies."""

    def test_extracts_single_block(self):
        body = (
            "Your technique has been assigned an ID.\n\n"
            "```json\n"
            '{"id": "DFT-1200", "name": "Test technique", "references": []}\n'
            "```\n"
        )
        result = mod.extract_json_block(body)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "DFT-1200")
        self.assertEqual(result["name"], "Test technique")

    def test_extracts_first_valid_block(self):
        body = (
            "Some preamble\n\n"
            "```json\n"
            '{"not_an_item": true}\n'
            "```\n\n"
            "```json\n"
            '{"id": "DFW-1050", "name": "Real weakness"}\n'
            "```\n"
        )
        result = mod.extract_json_block(body)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "DFW-1050")

    def test_returns_none_for_no_json(self):
        body = "Just a regular comment with no JSON."
        self.assertIsNone(mod.extract_json_block(body))

    def test_returns_none_for_invalid_json(self):
        body = "```json\n{invalid json}\n```"
        self.assertIsNone(mod.extract_json_block(body))

    def test_returns_none_for_json_without_id(self):
        body = '```json\n{"name": "no id field"}\n```'
        self.assertIsNone(mod.extract_json_block(body))

    def test_normalizes_old_format_id(self):
        body = (
            "Your mitigation has been assigned an ID.\n\n"
            "```json\n"
            '{"id": "M1240", "name": "Test mitigation", "references": []}\n'
            "```\n"
        )
        result = mod.extract_json_block(body)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "DFM-1240")

    def test_normalizes_old_technique_id(self):
        body = '```json\n{"id": "T1001", "name": "Test"}\n```'
        result = mod.extract_json_block(body)
        self.assertEqual(result["id"], "DFT-1001")

    def test_multiline_json_block(self):
        data = {
            "id": "DFM-1300",
            "name": "Multi-line mitigation",
            "references": [
                {"DFCite_id": "DFCite-1001", "relevance_summary_280": ""},
            ],
        }
        body = f"```json\n{json.dumps(data, indent=4)}\n```"
        result = mod.extract_json_block(body)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "DFM-1300")
        self.assertEqual(len(result["references"]), 1)


class TestFindAssignedComment(unittest.TestCase):
    """Test finding the assigned-ID comment from a list of comments."""

    def _make_comment(self, body):
        return {"body": body}

    def test_finds_assigned_comment(self):
        comments = [
            self._make_comment("Thanks for proposing a new technique!"),
            self._make_comment(
                'Technique ID **DFT-1200** has been assigned.\n\n'
                '```json\n{"id": "DFT-1200", "name": "Test"}\n```'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIsNotNone(result)
        self.assertIn("DFT-1200", result["body"])

    def test_ignores_preview_without_assignment(self):
        comments = [
            self._make_comment(
                'Thanks for proposing!\n\n'
                '```json\n{"id": "DFT-____", "name": "Test"}\n```'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIsNone(result)

    def test_returns_none_for_empty_comments(self):
        self.assertIsNone(mod.find_assigned_comment([]))

    def test_finds_weakness_assigned_comment(self):
        comments = [
            self._make_comment(
                'Weakness ID **DFW-1050** has been assigned.\n\n'
                '```json\n{"id": "DFW-1050", "name": "Test weakness"}\n```'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIsNotNone(result)

    def test_finds_old_format_assigned_comment(self):
        """Issue #279 style: old-format ID like M1240."""
        comments = [
            self._make_comment(
                'Thanks for proposing a new mitigation!\n\n'
                '```json\n{"id": "M____", "name": "Test"}\n```'
            ),
            self._make_comment('Assigned mitigation ID: **M1240**'),
            self._make_comment(
                'Your mitigation has been assigned an ID.\n\n'
                '```json\n{"id": "M1240", "name": "Test mitigation"}\n```\n\n'
                'Mitigation ID **M1240** has been assigned.'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIsNotNone(result)
        self.assertIn("M1240", result["body"])

    def test_fallback_finds_comment_without_assigned_text(self):
        """Issue #278 style: revised preview has real ID but no 'has been assigned' text."""
        comments = [
            self._make_comment(
                'Thanks for proposing a new technique!\n\n'
                '```json\n{"id": "T____", "name": "Test"}\n```'
            ),
            self._make_comment('Assigned technique ID: **T1165**'),
            self._make_comment(
                'Thanks for proposing a new technique!\n\n'
                '```json\n{"id": "T1165", "name": "Configuration file examination"}\n```\n\n'
                '---\n*This comment was automatically generated.*'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIsNotNone(result)
        self.assertIn("T1165", result["body"])

    def test_fallback_picks_last_comment_with_real_id(self):
        """When multiple comments have real IDs, pick the last one."""
        comments = [
            self._make_comment(
                '```json\n{"id": "DFT-1100", "name": "Old"}\n```'
            ),
            self._make_comment(
                '```json\n{"id": "DFT-1200", "name": "Newer"}\n```'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIsNotNone(result)
        self.assertIn("DFT-1200", result["body"])

    def test_prefers_has_been_assigned_over_fallback(self):
        """Primary match (with 'has been assigned') should win over fallback."""
        comments = [
            self._make_comment(
                '```json\n{"id": "DFT-1100", "name": "Fallback candidate"}\n```'
            ),
            self._make_comment(
                'Technique ID **DFT-1200** has been assigned.\n\n'
                '```json\n{"id": "DFT-1200", "name": "Primary match"}\n```'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIn("DFT-1200", result["body"])
        self.assertIn("has been assigned", result["body"])

    def test_finds_mitigation_assigned_comment(self):
        comments = [
            self._make_comment(
                'Mitigation ID **DFM-1300** has been assigned.\n\n'
                '```json\n{"id": "DFM-1300", "name": "Test mitigation"}\n```'
            ),
        ]
        result = mod.find_assigned_comment(comments)
        self.assertIsNotNone(result)


class TestHandleOldFormatReferences(unittest.TestCase):
    """Test conversion of old-format raw string references to DFCite format."""

    def setUp(self):
        """Create a temporary reference corpus."""
        self.tmpdir = tempfile.mkdtemp()
        refs_dir = os.path.join(self.tmpdir, "data", "references")
        os.makedirs(refs_dir)

        # Create a known reference
        with open(os.path.join(refs_dir, "DFCite-1001.txt"), "w") as f:
            f.write("Smith, J. (2024), Test Reference, https://example.com/test\n")

    def test_dict_refs_unchanged(self):
        """Dict-format references should pass through unchanged."""
        block = {
            "id": "DFT-1001",
            "references": [
                {"DFCite_id": "DFCite-1001", "relevance_summary_280": "relevant"},
            ],
        }
        refs, warnings = mod.handle_old_format_references(block, self.tmpdir)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["DFCite_id"], "DFCite-1001")
        self.assertEqual(refs[0]["relevance_summary_280"], "relevant")
        self.assertEqual(len(warnings), 0)

    def test_empty_refs_unchanged(self):
        block = {"id": "DFT-1001", "references": []}
        refs, warnings = mod.handle_old_format_references(block, self.tmpdir)
        self.assertEqual(refs, [])
        self.assertEqual(warnings, [])

    def test_no_refs_key(self):
        block = {"id": "DFT-1001"}
        refs, warnings = mod.handle_old_format_references(block, self.tmpdir)
        self.assertEqual(refs, [])
        self.assertEqual(warnings, [])

    def test_raw_string_matched_by_url(self):
        """A raw string with a matching URL should resolve to the DFCite ID."""
        block = {
            "id": "DFT-1001",
            "references": ["Some reference, https://example.com/test"],
        }
        refs, warnings = mod.handle_old_format_references(block, self.tmpdir)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["DFCite_id"], "DFCite-1001")
        self.assertEqual(refs[0]["relevance_summary_280"], "")
        self.assertEqual(len(warnings), 0)

    def test_raw_string_unmatched_gets_pending(self):
        """An unmatched raw string should get a PENDING placeholder."""
        block = {
            "id": "DFT-1001",
            "references": ["Completely unknown reference (2025)"],
        }
        refs, warnings = mod.handle_old_format_references(block, self.tmpdir)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["DFCite_id"], "PENDING")
        self.assertEqual(len(warnings), 1)
        self.assertIn("Could not match reference", warnings[0])

    def test_mixed_refs_handled(self):
        """Mix of dict and string refs should both be handled."""
        block = {
            "id": "DFT-1001",
            "references": [
                {"DFCite_id": "DFCite-1001", "relevance_summary_280": ""},
                "Unknown ref text here",
            ],
        }
        refs, warnings = mod.handle_old_format_references(block, self.tmpdir)
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0]["DFCite_id"], "DFCite-1001")
        self.assertEqual(refs[1]["DFCite_id"], "PENDING")
        self.assertEqual(len(warnings), 1)

    def test_empty_string_ref_skipped(self):
        block = {"id": "DFT-1001", "references": [""]}
        refs, warnings = mod.handle_old_format_references(block, self.tmpdir)
        self.assertEqual(refs, [])
        self.assertEqual(warnings, [])


class TestCheckDfciteExistence(unittest.TestCase):
    """Test DFCite file existence checks."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        refs_dir = os.path.join(self.tmpdir, "data", "references")
        os.makedirs(refs_dir)

        # Create one known reference
        with open(os.path.join(refs_dir, "DFCite-1001.txt"), "w") as f:
            f.write("A reference\n")

    def test_existing_ref_no_warning(self):
        block = {
            "id": "DFT-1001",
            "references": [
                {"DFCite_id": "DFCite-1001", "relevance_summary_280": ""},
            ],
        }
        warnings = mod.check_dfcite_existence(block, self.tmpdir)
        self.assertEqual(len(warnings), 0)

    def test_missing_ref_warns(self):
        block = {
            "id": "DFT-1001",
            "references": [
                {"DFCite_id": "DFCite-9999", "relevance_summary_280": ""},
            ],
        }
        warnings = mod.check_dfcite_existence(block, self.tmpdir)
        self.assertEqual(len(warnings), 1)
        self.assertIn("DFCite-9999", warnings[0])
        self.assertIn("does not exist", warnings[0])

    def test_pending_ref_no_warning(self):
        """PENDING refs should not trigger a warning about missing files."""
        block = {
            "id": "DFT-1001",
            "references": [
                {"DFCite_id": "PENDING", "relevance_summary_280": ""},
            ],
        }
        warnings = mod.check_dfcite_existence(block, self.tmpdir)
        self.assertEqual(len(warnings), 0)

    def test_no_references(self):
        block = {"id": "DFT-1001", "references": []}
        warnings = mod.check_dfcite_existence(block, self.tmpdir)
        self.assertEqual(len(warnings), 0)

    def test_non_dict_refs_skipped(self):
        block = {"id": "DFT-1001", "references": ["raw string"]}
        warnings = mod.check_dfcite_existence(block, self.tmpdir)
        self.assertEqual(len(warnings), 0)


class TestParseObjectiveFromIssue(unittest.TestCase):
    """Test objective extraction from issue body."""

    def test_extracts_objective(self):
        body = "### Objective\n\nAcquisition\n\n### Other field\n\nvalue"
        self.assertEqual(mod.parse_objective_from_issue(body), "Acquisition")

    def test_returns_none_if_missing(self):
        body = "### Some field\n\nvalue"
        self.assertIsNone(mod.parse_objective_from_issue(body))

    def test_strips_whitespace(self):
        body = "### Objective\n\n  Examination  \n\n"
        self.assertEqual(mod.parse_objective_from_issue(body), "Examination")


class TestWriteDataFile(unittest.TestCase):
    """Test writing data files to the correct locations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        for subdir in ("techniques", "weaknesses", "mitigations"):
            os.makedirs(os.path.join(self.tmpdir, "data", subdir))

    def test_writes_technique(self):
        block = {"id": "DFT-9999", "name": "Test", "references": []}
        path = mod.write_data_file(self.tmpdir, "technique", block)
        self.assertIsNotNone(path)
        self.assertTrue(os.path.exists(path))
        self.assertIn("techniques", path)

        with open(path) as f:
            data = json.load(f)
        self.assertEqual(data["id"], "DFT-9999")

    def test_writes_weakness(self):
        block = {"id": "DFW-9999", "name": "Test"}
        path = mod.write_data_file(self.tmpdir, "weakness", block)
        self.assertIsNotNone(path)
        self.assertIn("weaknesses", path)

    def test_writes_mitigation(self):
        block = {"id": "DFM-9999", "name": "Test"}
        path = mod.write_data_file(self.tmpdir, "mitigation", block)
        self.assertIsNotNone(path)
        self.assertIn("mitigations", path)

    def test_skips_existing_file(self):
        block = {"id": "DFT-9999", "name": "Test"}
        # Write once
        mod.write_data_file(self.tmpdir, "technique", block)
        # Write again — should skip
        path = mod.write_data_file(self.tmpdir, "technique", block)
        self.assertIsNone(path)

    def test_json_has_trailing_newline(self):
        block = {"id": "DFT-9999", "name": "Test"}
        path = mod.write_data_file(self.tmpdir, "technique", block)
        with open(path) as f:
            content = f.read()
        self.assertTrue(content.endswith('\n'))

    def test_json_is_indented(self):
        block = {"id": "DFT-9999", "name": "Test", "references": []}
        path = mod.write_data_file(self.tmpdir, "technique", block)
        with open(path) as f:
            content = f.read()
        self.assertIn('    "id"', content)


class TestUpdateSolveItJson(unittest.TestCase):
    """Test solve-it.json updates for techniques."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmpdir, "data"))
        self.solve_it = [
            {"name": "Acquisition", "techniques": ["DFT-1001"]},
            {"name": "Examination", "techniques": []},
        ]
        with open(os.path.join(self.tmpdir, "data", "solve-it.json"), "w") as f:
            json.dump(self.solve_it, f)

    def test_adds_technique_to_objective(self):
        result = mod.update_solve_it_json(self.tmpdir, "Examination", "DFT-9999")
        self.assertTrue(result)

        with open(os.path.join(self.tmpdir, "data", "solve-it.json")) as f:
            data = json.load(f)
        self.assertIn("DFT-9999", data[1]["techniques"])

    def test_skips_duplicate(self):
        result = mod.update_solve_it_json(self.tmpdir, "Acquisition", "DFT-1001")
        self.assertTrue(result)

        with open(os.path.join(self.tmpdir, "data", "solve-it.json")) as f:
            data = json.load(f)
        self.assertEqual(data[0]["techniques"].count("DFT-1001"), 1)

    def test_returns_false_for_unknown_objective(self):
        result = mod.update_solve_it_json(self.tmpdir, "Nonexistent", "DFT-9999")
        self.assertFalse(result)


class TestFindCrossReferences(unittest.TestCase):
    """Test cross-reference detection."""

    def test_weakness_mitigation_crossref(self):
        block = {"id": "DFW-1050", "mitigations": ["DFM-1001", "DFM-1002"]}
        notes = mod.find_cross_references(block, "weakness")
        self.assertEqual(len(notes), 2)
        self.assertIn("DFM-1001", notes[0])

    def test_technique_weakness_crossref(self):
        block = {"id": "DFT-1200", "weaknesses": ["DFW-1001"]}
        notes = mod.find_cross_references(block, "technique")
        self.assertEqual(len(notes), 1)
        self.assertIn("DFW-1001", notes[0])

    def test_no_crossrefs_for_empty_lists(self):
        block = {"id": "DFT-1200", "weaknesses": []}
        notes = mod.find_cross_references(block, "technique")
        self.assertEqual(len(notes), 0)

    def test_invalid_ids_ignored(self):
        block = {"id": "DFW-1050", "mitigations": ["not-a-valid-id"]}
        notes = mod.find_cross_references(block, "weakness")
        self.assertEqual(len(notes), 0)


class TestSlugify(unittest.TestCase):

    def test_basic_slug(self):
        self.assertEqual(mod.slugify("Test Technique"), "test-technique")

    def test_special_characters(self):
        self.assertEqual(mod.slugify("Foo & Bar's (test)"), "foo-bar-s-test")

    def test_truncation(self):
        result = mod.slugify("A" * 100, max_len=10)
        self.assertLessEqual(len(result), 10)

    def test_no_trailing_hyphens(self):
        result = mod.slugify("test---", max_len=50)
        self.assertFalse(result.endswith('-'))


class TestSanitiseGitValue(unittest.TestCase):

    def test_strips_angle_brackets(self):
        self.assertEqual(mod.sanitise_git_value("Foo <Bar>"), "Foo Bar")

    def test_strips_newlines(self):
        self.assertEqual(mod.sanitise_git_value("Foo\nBar"), "FooBar")

    def test_normal_name_unchanged(self):
        self.assertEqual(mod.sanitise_git_value("John Smith"), "John Smith")


if __name__ == "__main__":
    unittest.main()
