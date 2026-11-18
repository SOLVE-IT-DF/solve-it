"""Tests for revising a TRWM submission through a revision comment:
admin/apply_trwm_revision.py, admin/trwm_revision_diff.py and the revision
support in admin/issue_parsers/parse_trwm_submission.py."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'admin', 'issue_parsers'))
sys.path.insert(0, os.path.join(ROOT, 'admin'))

from parse_trwm_submission import (  # noqa: E402
    SubmissionError, add_preview_hash, generate_preview, load_trwm_json,
    preview_hash, stored_preview_hash,
)
from trwm_revision_diff import diff_previews, preview_items, render_summary  # noqa: E402
from apply_trwm_revision import (  # noqa: E402
    build_failure_reply, build_success_reply, can_revise, current_revision_number,
    extract_revision_json, find_preview_comment, ids_assigned, labels_to_add,
    preview_was_hand_edited,
)


def make_export():
    """A small export shaped like the TRWM Helper's, modelled on a real
    submission: one new technique, two new weaknesses, no mitigations."""
    return {
        "generatedBy": {"app": "TRWM SOLVE-IT Helper", "version": "3.12.2"},
        "techniques": {
            "DFT-temp-0001": {
                "id": "DFT-temp-0001",
                "name": "Recovery of Chat log file(s)",
                "description": "Recover traces of chat activity from log files.",
                "synonyms": [], "details": "", "parent_technique": "",
                "subtechniques": [], "examples": [],
                "weaknesses": ["DFW-temp-0001", "DFW-temp-0002"],
                "CASE_input_classes": [], "CASE_output_classes": [],
                "references": [],
            }
        },
        "weaknesses": {
            "DFW-temp-0001": {
                "id": "DFW-temp-0001",
                "name": "Log files may only store data for a limited period of time because",
                "description": "", "categories": ["ASTM_INCOMP"],
                "mitigations": [], "references": [],
            },
            "DFW-temp-0002": {
                "id": "DFW-temp-0002",
                "name": "Log files may only store data for a limited period of time",
                "description": "", "categories": ["ASTM_INCOMP"],
                "mitigations": [], "references": [],
            },
        },
        "mitigations": {},
    }


def make_body(export):
    return (
        "### Submission type\n\nNew technique\n\n"
        "### Objective\n\nExtract artifacts stored by applications\n\n"
        "### TRWM Helper JSON export\n\n```json\n"
        + json.dumps(export, indent=2) + "\n```\n\n"
        "### Additional notes\n\n_No response_\n"
    )


def preview_for(export, revision_info=None):
    comment, labels = generate_preview(make_body(make_export()), None,
                                       trwm_data=copy.deepcopy(export),
                                       revision_info=revision_info)
    return comment, labels


def revision_comment(export, heading="### TRWM revision"):
    return (f"{heading}\n\nRenamed the technique.\n\n```json\n"
            + json.dumps(export, indent=2) + "\n```\n")


class TestGeneratePreview(unittest.TestCase):

    def test_body_and_revision_json_give_the_same_preview(self):
        from_body, labels_body = generate_preview(make_body(make_export()))
        from_revision, labels_rev = preview_for(make_export())
        self.assertEqual(from_body, from_revision)
        self.assertEqual(labels_body, labels_rev)

    def test_revision_json_replaces_body_json(self):
        export = make_export()
        export["techniques"]["DFT-temp-0001"]["name"] = "Recover chat data from secondary log file(s)"
        comment, _ = preview_for(export)
        self.assertIn("Recover chat data from secondary log file(s)", comment)
        self.assertNotIn("Recovery of Chat log file(s)", comment)

    def test_form_fields_still_come_from_body(self):
        comment, _ = preview_for(make_export())
        self.assertIn("**Objective:** Extract artifacts stored by applications", comment)

    def test_no_revision_markers_without_revision_info(self):
        comment, _ = preview_for(make_export())
        self.assertNotIn("TRWM_SOURCE", comment)
        self.assertNotIn("**Revision", comment)

    def test_revision_markers(self):
        info = {"comment_id": 987, "revision": 3, "user": "someone", "date": "2026-11-18"}
        comment, _ = preview_for(make_export(), revision_info=info)
        self.assertTrue(comment.startswith("<!-- TRWM_PREVIEW -->\n<!-- TRWM_SOURCE: comment 987 revision 3 -->"))
        self.assertIn("**Revision 3**, from @someone's comment of 2026-11-18.", comment)

    def test_missing_body_json_raises(self):
        body = "### Submission type\n\nNew technique\n\n### TRWM Helper JSON export\n\n_No response_\n"
        with self.assertRaises(SubmissionError):
            generate_preview(body)

    def test_cli_revision_json_file(self):
        export = make_export()
        export["weaknesses"]["DFW-temp-0002"]["name"] = "Renamed by revision"
        with tempfile.TemporaryDirectory() as d:
            body_file = os.path.join(d, "body.md")
            json_file = os.path.join(d, "rev.json")
            out_file = os.path.join(d, "out.md")
            with open(body_file, "w") as f:
                f.write(make_body(make_export()))
            with open(json_file, "w") as f:
                json.dump(export, f)
            subprocess.run(
                [sys.executable, os.path.join(ROOT, "admin", "issue_parsers", "parse_trwm_submission.py"),
                 "--issue-body-file", body_file, "--revision-json-file", json_file,
                 "--revision-comment-id", "5", "--revision-number", "2",
                 "--revision-user", "someone", "--revision-date", "2026-11-18",
                 "--output", out_file],
                check=True, capture_output=True, text=True)
            with open(out_file) as f:
                out = f.read()
        self.assertIn("Renamed by revision", out)
        self.assertIn("<!-- TRWM_SOURCE: comment 5 revision 2 -->", out)


class TestLoadTrwmJson(unittest.TestCase):

    def test_valid(self):
        self.assertIn("techniques", load_trwm_json(json.dumps(make_export())))

    def test_malformed(self):
        with self.assertRaises(SubmissionError):
            load_trwm_json("{not json")

    def test_missing_key(self):
        export = make_export()
        del export["mitigations"]
        with self.assertRaises(SubmissionError):
            load_trwm_json(json.dumps(export))

    def test_not_an_object(self):
        with self.assertRaises(SubmissionError):
            load_trwm_json("[1, 2]")


class TestPreviewHash(unittest.TestCase):

    def test_generated_preview_carries_matching_hash(self):
        comment, _ = preview_for(make_export())
        self.assertIsNotNone(stored_preview_hash(comment))
        self.assertEqual(stored_preview_hash(comment), preview_hash(comment))
        self.assertFalse(preview_was_hand_edited(comment))

    def test_hand_edit_detected(self):
        comment, _ = preview_for(make_export())
        edited = comment.replace("Log files may only store data for a limited period of time\"",
                                 "Log files are kept briefly\"")
        self.assertNotEqual(edited, comment)
        self.assertTrue(preview_was_hand_edited(edited))

    def test_github_line_endings_and_trailing_space_ignored(self):
        comment, _ = preview_for(make_export())
        resaved = "\r\n".join(line + "  " for line in comment.split("\n"))
        self.assertFalse(preview_was_hand_edited(resaved))

    def test_preview_without_hash_is_not_flagged(self):
        self.assertFalse(preview_was_hand_edited("<!-- TRWM_PREVIEW -->\nold preview\n"))

    def test_add_preview_hash_replaces_existing_marker(self):
        once = add_preview_hash("<!-- TRWM_PREVIEW -->\nbody\n")
        twice = add_preview_hash(once)
        self.assertEqual(once, twice)
        self.assertEqual(twice.count("TRWM_PREVIEW_HASH"), 1)


class TestRevisionDiff(unittest.TestCase):

    def setUp(self):
        self.old, _ = preview_for(make_export())

    def test_no_change(self):
        new, _ = preview_for(make_export())
        diff = diff_previews(self.old, new)
        self.assertEqual(diff, {"added": [], "removed": [], "changed": []})
        self.assertIn("No changes", render_summary(diff))

    def test_rename(self):
        export = make_export()
        export["weaknesses"]["DFW-temp-0001"]["name"] = "Older chat logs removed after power-on"
        new, _ = preview_for(export)
        diff = diff_previews(self.old, new)
        self.assertEqual(diff["changed"],
                         [("DFW-temp-0001", "Older chat logs removed after power-on", ["name"])])
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])

    def test_add_new_mitigation(self):
        export = make_export()
        export["mitigations"]["DFM-temp-0001"] = {
            "id": "DFM-temp-0001", "name": "Acquire before powering on",
            "description": "", "technique": "", "references": []}
        export["weaknesses"]["DFW-temp-0002"]["mitigations"] = ["DFM-temp-0001"]
        new, _ = preview_for(export)
        diff = diff_previews(self.old, new)
        self.assertEqual(diff["added"], [("DFM-temp-0001", "Acquire before powering on")])
        self.assertEqual(diff["changed"],
                         [("DFW-temp-0002", export["weaknesses"]["DFW-temp-0002"]["name"],
                           ["mitigations"])])

    def test_delete_first_weakness_does_not_look_like_a_rename(self):
        # Placeholders renumber when the first weakness goes (DFW-____-2
        # becomes DFW-____-1); matching on temp IDs must see through that.
        export = make_export()
        del export["weaknesses"]["DFW-temp-0001"]
        export["techniques"]["DFT-temp-0001"]["weaknesses"] = ["DFW-temp-0002"]
        new, _ = preview_for(export)
        self.assertIn("DFW-____-1", new)
        diff = diff_previews(self.old, new)
        self.assertEqual(diff["removed"], [
            ("DFW-temp-0001", "Log files may only store data for a limited period of time because")])
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["changed"],
                         [("DFT-temp-0001", "Recovery of Chat log file(s)", ["weaknesses"])])

    def test_items_keyed_by_temp_id(self):
        self.assertEqual(sorted(preview_items(self.old)),
                         ["DFT-temp-0001", "DFW-temp-0001", "DFW-temp-0002"])

    def test_new_references_compared_by_citation_text(self):
        a = make_export()
        a["techniques"]["DFT-temp-0001"]["references"] = ["Author (2019). A \"quoted\" title."]
        b = copy.deepcopy(a)
        b["weaknesses"]["DFW-temp-0001"]["references"] = ["Another (2026). Second source."]
        old, _ = preview_for(a)
        new, _ = preview_for(b)
        diff = diff_previews(old, new)
        self.assertEqual([k for k, _, _ in diff["changed"]], ["DFW-temp-0001"])

    def test_summary_lists_each_kind(self):
        diff = {"added": [("DFM-temp-0001", "M")], "removed": [("DFW-temp-0001", "W")],
                "changed": [("DFT-temp-0001", "T", ["description", "name"])]}
        summary = render_summary(diff)
        self.assertIn("**Added** mitigation `DFM-temp-0001` (M)", summary)
        self.assertIn("**Removed** weakness `DFW-temp-0001` (W)", summary)
        self.assertIn("**Changed** technique `DFT-temp-0001` (T): `description`, `name`", summary)

    def test_summary_leaves_out_empty_names(self):
        diff = {"added": [], "removed": [], "changed": [("DFT-temp-0001", "", ["details"])]}
        self.assertIn("**Changed** technique `DFT-temp-0001`: `details`", render_summary(diff))


class TestPermission(unittest.TestCase):

    def test_issue_author(self):
        self.assertTrue(can_revise("submitter", "submitter", "NONE"))
        self.assertTrue(can_revise("Submitter", "submitter", "CONTRIBUTOR"))

    def test_trusted_associations(self):
        for assoc in ("OWNER", "MEMBER", "COLLABORATOR", "collaborator"):
            self.assertTrue(can_revise("maintainer", "submitter", assoc), assoc)

    def test_others_refused(self):
        for assoc in ("NONE", "CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "", None):
            self.assertFalse(can_revise("stranger", "submitter", assoc), assoc)

    def test_empty_names_do_not_match(self):
        self.assertFalse(can_revise("", "", "NONE"))


class TestLabelsAndState(unittest.TestCase):

    def test_assigned_label_blocks(self):
        self.assertTrue(ids_assigned(["trwm", "assigned ID"]))
        self.assertFalse(ids_assigned(["trwm"]))

    def test_labels_only_added(self):
        self.assertEqual(
            labels_to_add(["content: new technique", "content: new mitigation"],
                          ["trwm", "content: new technique", "content: new weakness"]),
            ["content: new mitigation"])

    def test_labels_from_revision_include_new_mitigation(self):
        export = make_export()
        export["mitigations"]["DFM-temp-0001"] = {
            "id": "DFM-temp-0001", "name": "M", "description": "", "technique": "", "references": []}
        _, labels = preview_for(export)
        self.assertIn("content: new mitigation", labels)

    def test_first_preview_comment_wins(self):
        comments = [{"id": 1, "body": "hello"},
                    {"id": 2, "body": "<!-- TRWM_PREVIEW -->\nfirst"},
                    {"id": 3, "body": "<!-- TRWM_PREVIEW -->\nhas been assigned"}]
        self.assertEqual(find_preview_comment(comments)["id"], 2)
        self.assertIsNone(find_preview_comment([{"id": 1, "body": None}]))

    def test_revision_numbering(self):
        self.assertEqual(current_revision_number("<!-- TRWM_PREVIEW -->"), 1)
        info = {"comment_id": 9, "revision": 4, "user": "u", "date": "2026-11-18"}
        comment, _ = preview_for(make_export(), revision_info=info)
        self.assertEqual(current_revision_number(comment), 4)


class TestExtractRevisionJson(unittest.TestCase):

    def test_valid(self):
        data = extract_revision_json(revision_comment(make_export()))
        self.assertIn("DFT-temp-0001", data["techniques"])

    def test_plain_fence_and_crlf(self):
        body = revision_comment(make_export()).replace("```json", "```").replace("\n", "\r\n")
        self.assertIn("weaknesses", extract_revision_json(body))

    def test_missing_heading(self):
        with self.assertRaises(SubmissionError):
            extract_revision_json("```json\n{}\n```\n")

    def test_missing_block(self):
        with self.assertRaisesRegex(SubmissionError, "No fenced JSON block"):
            extract_revision_json("### TRWM revision\n\nForgot to paste it.\n")

    def test_block_before_heading_is_ignored(self):
        body = "```json\n" + json.dumps(make_export()) + "\n```\n\n### TRWM revision\n\nnothing\n"
        with self.assertRaises(SubmissionError):
            extract_revision_json(body)

    def test_malformed_json(self):
        with self.assertRaisesRegex(SubmissionError, "Invalid JSON"):
            extract_revision_json("### TRWM revision\n\n```json\n{\"techniques\": \n```\n")

    def test_wrong_shape(self):
        with self.assertRaisesRegex(SubmissionError, "Missing required key"):
            extract_revision_json("### TRWM revision\n\n```json\n{\"techniques\": {}}\n```\n")


class TestReplies(unittest.TestCase):

    def test_success_reply(self):
        reply = build_success_reply(2, 1, "- **Changed** ...", "https://example/preview", False)
        self.assertIn("**Revision 2 applied**", reply)
        self.assertIn("Changes since revision 1:", reply)
        self.assertNotIn(":warning:", reply)

    def test_success_reply_warns_on_hand_edit(self):
        reply = build_success_reply(2, 1, "x", "u", True)
        self.assertIn(":warning:", reply)
        self.assertIn('"edited" history', reply)
        self.assertIn("send another revision", reply)

    def test_replies_never_retrigger_the_workflow(self):
        # The workflow runs on any comment containing the heading text; the
        # bot is excluded by name, but its replies must not contain it either.
        for reply in (build_success_reply(2, 1, "x", "u", True), build_failure_reply("why")):
            self.assertNotIn("### TRWM revision", reply)


if __name__ == '__main__':
    unittest.main()
