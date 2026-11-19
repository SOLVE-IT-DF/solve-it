"""Tests for converting a non-TRWM issue into a TRWM submission:
admin/convert_to_trwm.py, the form-field fallback in
admin/issue_parsers/parse_trwm_submission.py, and autoimplement reading the
preview's record of the form fields."""

import copy
import json
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'admin', 'issue_parsers'))
sys.path.insert(0, os.path.join(ROOT, 'admin'))

from parse_trwm_submission import (  # noqa: E402
    SubmissionError, form_marker, generate_preview, read_form_marker,
    resolve_form_fields,
)
from parse_technique_issue import parse_issue_body  # noqa: E402
from apply_trwm_revision import current_revision_number  # noqa: E402
from convert_to_trwm import (  # noqa: E402
    extract_export, find_source_comment, has_export_heading, refusal_reason,
)
from autoimplement_trwm import body_has_trwm_form, form_fields_from_comments  # noqa: E402


# The body of a placeholder issue opened with the old "new technique" form,
# like #271, which has none of the TRWM form's fields.
PLACEHOLDER_BODY = (
    "### Technique name:\nExtract data from SIM card\n\n"
    "### Description:\nTODO\n\n"
    "### Notes:\nTODO\n"
)


def make_export(objective="Acquire data", technique_id="DFT-temp-0001", parent=""):
    return {
        "generatedBy": {"app": "TRWM SOLVE-IT Helper", "version": "3.17.0"},
        "techniques": {
            technique_id: {
                "id": technique_id,
                "name": "Extract data from a SIM card",
                "description": "Read the file system of a SIM card.",
                "synonyms": [], "details": "", "parent_technique": parent,
                "subtechniques": [], "examples": [],
                "weaknesses": ["DFW-temp-0001"],
                "CASE_input_classes": [], "CASE_output_classes": [],
                "references": [],
            }
        },
        "weaknesses": {
            "DFW-temp-0001": {
                "id": "DFW-temp-0001",
                "name": "Failure to recover contacts from a SIM card",
                "description": "", "categories": ["ASTM_INCOMP"],
                "mitigations": [], "references": [],
            },
        },
        "mitigations": {},
        **({"objective": objective} if objective is not None else {}),
    }


def form_body(export, objective="Extract artifacts stored by applications",
              submission_type="New technique"):
    return (
        f"### Submission type\n\n{submission_type}\n\n"
        f"### Objective\n\n{objective}\n\n"
        "### TRWM Helper JSON export\n\n```json\n"
        + json.dumps(export, indent=2) + "\n```\n"
    )


def comment(body, login="chrishargreaves", association="OWNER", cid=1, created="2026-11-19T12:00:00Z"):
    return {"id": cid, "body": body, "created_at": created,
            "user": {"login": login}, "author_association": association}


def export_comment(export, heading="### TRWM revision"):
    return f"{heading}\n\n```json\n" + json.dumps(export, indent=2) + "\n```\n"


class TestResolveFormFields(unittest.TestCase):

    def test_form_fields_take_precedence(self):
        fields = parse_issue_body(form_body(make_export()))
        resolved, notes = resolve_form_fields(fields, make_export())
        self.assertEqual(resolved["submission_type"], "New technique")
        self.assertEqual(resolved["objective"], "Extract artifacts stored by applications")

    def test_form_and_export_disagreeing_is_flagged(self):
        fields = parse_issue_body(form_body(make_export()))
        _, notes = resolve_form_fields(fields, make_export(objective="Acquire data"))
        self.assertTrue(any(level == "warning" and "Acquire data" in msg for level, msg in notes))

    def test_matching_export_objective_is_not_flagged(self):
        fields = parse_issue_body(form_body(make_export(), objective="Acquire data"))
        _, notes = resolve_form_fields(fields, make_export(objective="Acquire data"))
        self.assertEqual(notes, [])

    def test_no_form_takes_objective_from_export(self):
        fields = parse_issue_body(PLACEHOLDER_BODY)
        resolved, notes = resolve_form_fields(fields, make_export())
        self.assertEqual(resolved["submission_type"], "New technique")
        self.assertEqual(resolved["objective"], "Acquire data")
        self.assertEqual(resolved["proposed_objective"], "")
        self.assertTrue(any(level == "info" for level, _ in notes))

    def test_no_form_real_technique_id_is_an_update(self):
        fields = parse_issue_body(PLACEHOLDER_BODY)
        resolved, _ = resolve_form_fields(fields, make_export(technique_id="DFT-1002"))
        self.assertEqual(resolved["submission_type"], "Update existing technique")

    def test_unknown_export_objective_is_a_proposal(self):
        fields = parse_issue_body(PLACEHOLDER_BODY)
        resolved, _ = resolve_form_fields(
            fields, make_export(objective="Examine SIM cards"),
            known_objectives={"Acquire data"})
        self.assertEqual(resolved["objective"], "")
        self.assertEqual(resolved["proposed_objective"], "Examine SIM cards")

    def test_no_form_and_no_export_objective_warns(self):
        fields = parse_issue_body(PLACEHOLDER_BODY)
        resolved, notes = resolve_form_fields(fields, make_export(objective=None))
        self.assertEqual(resolved["objective"], "")
        self.assertTrue(any(level == "warning" for level, _ in notes))

    def test_form_with_other_objective(self):
        body = form_body(make_export(), objective="Other (specify below)") + \
            "\n### Propose new objective\n\nExamine SIM cards\n"
        resolved, _ = resolve_form_fields(parse_issue_body(body), make_export(objective=None))
        self.assertEqual(resolved["objective"], "")
        self.assertEqual(resolved["proposed_objective"], "Examine SIM cards")


class TestFormMarker(unittest.TestCase):

    def test_round_trip(self):
        resolved = {"submission_type": "New technique", "objective": "Acquire data",
                    "proposed_objective": ""}
        marker = form_marker(resolved, "DFT-1002")
        data = read_form_marker("text\n" + marker + "\nmore")
        self.assertEqual(data["objective"], "Acquire data")
        self.assertEqual(data["parent_technique"], "DFT-1002")

    def test_value_cannot_close_the_html_comment(self):
        resolved = {"submission_type": "New technique", "objective": "",
                    "proposed_objective": "A --> B"}
        marker = form_marker(resolved, "")
        self.assertEqual(marker.count("-->"), 1)
        self.assertEqual(read_form_marker(marker)["proposed_objective"], "A --> B")


class TestConvertedPreview(unittest.TestCase):

    def preview(self, export=None, info=None):
        info = info or {"comment_id": 55, "revision": 1, "user": "chrishargreaves",
                        "date": "2026-11-19", "converted": True}
        return generate_preview(PLACEHOLDER_BODY, None,
                                trwm_data=copy.deepcopy(export or make_export()),
                                revision_info=info)

    def test_preview_from_a_placeholder_issue(self):
        text, labels = self.preview()
        self.assertIn("**Converted to a TRWM submission** from @chrishargreaves's comment", text)
        self.assertIn("**Objective:** Acquire data", text)
        self.assertIn("<!-- TRWM_SOURCE: comment 55 revision 1 -->", text)
        self.assertIn("content: new technique", labels)
        self.assertEqual(read_form_marker(text)["objective"], "Acquire data")

    def test_next_revision_is_two(self):
        text, _ = self.preview()
        self.assertEqual(current_revision_number(text), 1)

    def test_revision_of_a_converted_issue_keeps_the_objective(self):
        export = make_export()
        export["techniques"]["DFT-temp-0001"]["name"] = "Extract data from a UICC"
        info = {"comment_id": 77, "revision": 2, "user": "chrishargreaves", "date": "2026-11-20"}
        text, _ = self.preview(export, info)
        self.assertIn("**Revision 2**", text)
        self.assertIn("**Objective:** Acquire data", text)

    def test_parent_from_export_is_recorded(self):
        text, _ = self.preview(make_export(parent="DFT-1002"))
        self.assertEqual(read_form_marker(text)["parent_technique"], "DFT-1002")

    def test_form_issue_preview_also_carries_the_marker(self):
        text, _ = generate_preview(form_body(make_export(objective=None)))
        data = read_form_marker(text)
        self.assertEqual(data["objective"], "Extract artifacts stored by applications")
        self.assertEqual(data["submission_type"], "New technique")


class TestConvertRules(unittest.TestCase):

    def test_refuses_an_existing_trwm_issue(self):
        self.assertIsNotNone(refusal_reason(["trwm"], False))
        self.assertIsNotNone(refusal_reason([], True))

    def test_refuses_once_ids_are_assigned(self):
        self.assertIsNotNone(refusal_reason(["assigned ID", "content: new technique"], False))

    def test_accepts_a_placeholder_issue(self):
        self.assertIsNone(refusal_reason(["content: new technique"], False))

    def test_headings(self):
        self.assertTrue(has_export_heading("### TRWM revision\n\n```json\n{}\n```"))
        self.assertTrue(has_export_heading("### TRWM submission\n"))
        self.assertFalse(has_export_heading("Please use `### TRWM revision` next time"))

    def test_newest_comment_from_author_or_maintainer(self):
        comments = [
            comment(export_comment(make_export()), cid=1),
            comment(export_comment(make_export()), login="stranger", association="NONE", cid=2),
            comment("Thanks!", cid=3),
            comment(export_comment(make_export(), "### TRWM submission"), login="author",
                    association="NONE", cid=4),
            comment(export_comment(make_export()), login="github-actions[bot]", association="NONE", cid=5),
        ]
        self.assertEqual(find_source_comment(comments, "author")["id"], 4)
        self.assertEqual(find_source_comment(comments[:3], "author")["id"], 1)
        self.assertIsNone(find_source_comment(comments[1:3], "author"))

    def test_extract_export(self):
        data = extract_export(export_comment(make_export(), "### TRWM submission"))
        self.assertEqual(data["objective"], "Acquire data")
        with self.assertRaises(SubmissionError):
            extract_export("### TRWM submission\n\nno json here")


class TestAutoimplementFormFields(unittest.TestCase):

    def test_reads_marker_preferring_the_assigned_preview(self):
        first, _ = generate_preview(PLACEHOLDER_BODY, None, trwm_data=make_export(objective="Acquire data"))
        assigned, _ = generate_preview(PLACEHOLDER_BODY, None, trwm_data=make_export(objective="Conduct research"))
        assigned = assigned.replace("Thanks for your", "ID has been assigned. Thanks for your")
        data = form_fields_from_comments([{"body": first}, {"body": "chat"}, {"body": assigned}])
        self.assertEqual(data["objective"], "Conduct research")

    def test_only_issues_without_the_form_use_the_marker(self):
        self.assertTrue(body_has_trwm_form(form_body(make_export())))
        self.assertFalse(body_has_trwm_form(PLACEHOLDER_BODY))

    def test_old_previews_without_marker_give_none(self):
        self.assertIsNone(form_fields_from_comments([{"body": "<!-- TRWM_PREVIEW -->\nold"}]))


if __name__ == '__main__':
    unittest.main()
