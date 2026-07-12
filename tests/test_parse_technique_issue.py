"""Tests for admin/issue_parsers/parse_technique_issue.py — including the
parent technique (subtechnique) field."""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_technique_issue import (
    build_comment,
    build_technique_json,
    parse_issue_body,
)


def _make_fields(parent=""):
    return {
        "Technique name": "Test technique",
        "Description": "A test description.",
        "Synonyms": "",
        "Details": "",
        "Examples": "",
        "Objective": "Review content for relevance",
        "Propose new objective": "_No response_",
        "Parent technique ID": parent,
        "Existing weakness IDs": "",
        "Propose new weaknesses": "",
        "Ontology input classes": "",
        "Ontology output classes": "",
        "References": "",
    }


class TestParseIssueBody(unittest.TestCase):

    def test_parses_parent_technique_field(self):
        body = (
            "### Technique name\n\nTest technique\n\n"
            "### Parent technique ID\n\nDFT-1079\n\n"
            "### Any other notes\n\n_No response_\n"
        )
        fields = parse_issue_body(body)
        self.assertEqual(fields["Parent technique ID"], "DFT-1079")

    def test_missing_parent_technique_field(self):
        body = "### Technique name\n\nTest technique\n"
        fields = parse_issue_body(body)
        self.assertNotIn("Parent technique ID", fields)


class TestBuildTechniqueJsonParent(unittest.TestCase):

    def test_parent_included_when_given(self):
        technique, _, _, _ = build_technique_json(_make_fields("DFT-1079"))
        self.assertEqual(technique["_parent_techniques"], ["DFT-1079"])

    def test_parent_absent_when_blank(self):
        technique, _, _, _ = build_technique_json(_make_fields(""))
        self.assertNotIn("_parent_techniques", technique)

    def test_parent_absent_when_no_response(self):
        technique, _, _, _ = build_technique_json(_make_fields("_No response_"))
        self.assertNotIn("_parent_techniques", technique)

    def test_parent_absent_when_field_missing(self):
        fields = _make_fields()
        del fields["Parent technique ID"]
        technique, _, _, _ = build_technique_json(fields)
        self.assertNotIn("_parent_techniques", technique)

    def test_subtechniques_still_empty_list(self):
        technique, _, _, _ = build_technique_json(_make_fields("DFT-1079"))
        self.assertEqual(technique["subtechniques"], [])

    def test_whitespace_stripped(self):
        technique, _, _, _ = build_technique_json(_make_fields("  DFT-1079  "))
        self.assertEqual(technique["_parent_techniques"], ["DFT-1079"])


class TestBuildCommentParent(unittest.TestCase):

    def _json_block(self, comment):
        match = re.search(r'```json\s*\n(.*?)\n```', comment, re.DOTALL)
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_comment_mentions_parent(self):
        fields = _make_fields("DFT-1079")
        technique, _, _, _ = build_technique_json(fields)
        comment = build_comment(technique, fields)
        self.assertIn("### Parent technique", comment)
        self.assertIn("DFT-1079", comment)
        self.assertIn("subtechnique", comment)

    def test_comment_json_carries_parent(self):
        """The preview JSON must include _parent_techniques so that the
        assign-ID and autoimplement steps can pick it up from the comment."""
        fields = _make_fields("DFT-1079")
        technique, _, _, _ = build_technique_json(fields)
        comment = build_comment(technique, fields)
        block = self._json_block(comment)
        self.assertEqual(block["_parent_techniques"], ["DFT-1079"])

    def test_comment_no_parent_section_without_parent(self):
        fields = _make_fields("")
        technique, _, _, _ = build_technique_json(fields)
        comment = build_comment(technique, fields)
        self.assertNotIn("### Parent technique", comment)
        self.assertNotIn("_parent_techniques", comment)

    def test_comment_warns_on_invalid_parent_id(self):
        fields = _make_fields("Examine audio content")
        technique, _, _, _ = build_technique_json(fields)
        comment = build_comment(technique, fields)
        self.assertIn(":warning:", comment)
        self.assertIn("does not look like a valid technique ID", comment)

    def test_comment_accepts_old_format_id(self):
        fields = _make_fields("T1079")
        technique, _, _, _ = build_technique_json(fields)
        comment = build_comment(technique, fields)
        self.assertNotIn("does not look like a valid technique ID", comment)


class TestEndToEndBody(unittest.TestCase):
    """Simulate a full GitHub form body through parse + build + comment."""

    BODY = (
        "### Technique name\n\n"
        "Classify if audio is potentially synthetically generated\n\n"
        "### Description\n\n"
        "```text\nClassification of audio with respect to its origin.\n```\n\n"
        "### Synonyms\n\n"
        "```text\nAudio deepfake detection\n```\n\n"
        "### Objective\n\n"
        "Review content for relevance\n\n"
        "### Propose new objective\n\n"
        "_No response_\n\n"
        "### Parent technique ID\n\n"
        "DFT-1079\n\n"
        "### Existing weakness IDs\n\n"
        "```text\n\n```\n\n"
        "### Any other notes\n\n"
        "_No response_\n"
    )

    def test_full_flow(self):
        fields = parse_issue_body(self.BODY)
        technique, _, _, _ = build_technique_json(fields)
        self.assertEqual(technique["_parent_techniques"], ["DFT-1079"])
        comment = build_comment(technique, fields)
        match = re.search(r'```json\s*\n(.*?)\n```', comment, re.DOTALL)
        block = json.loads(match.group(1))
        self.assertEqual(block["name"],
                         "Classify if audio is potentially synthetically generated")
        self.assertEqual(block["_parent_techniques"], ["DFT-1079"])


if __name__ == '__main__':
    unittest.main()
