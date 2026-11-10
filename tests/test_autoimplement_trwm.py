"""Tests for subtechnique placement in admin/autoimplement_trwm.py."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
import autoimplement_trwm as mod


def issue_body(parent="_No response_", export_parent=""):
    export = {"techniques": {"DFT-temp-0001": {"name": "T", "parent_technique": export_parent}},
              "weaknesses": {}, "mitigations": {}}
    return (
        "### Submission type\n\nNew technique\n\n"
        "### Objective\n\nExtract data from specific formats\n\n"
        f"### Parent technique (optional)\n\n{parent}\n\n"
        "### TRWM Helper JSON export\n\n```json\n"
        f"{json.dumps(export, indent=2)}\n```\n\n"
        "### Additional notes\n\n_No response_\n"
    )


class TestParseParentTechnique(unittest.TestCase):

    def test_form_field(self):
        self.assertEqual(mod.parse_parent_technique_from_issue(issue_body("DFT-1205")),
                         ("DFT-1205", None))

    def test_no_parent(self):
        self.assertEqual(mod.parse_parent_technique_from_issue(issue_body()), (None, None))

    def test_export_fallback(self):
        body = issue_body(export_parent="DFT-1049")
        self.assertEqual(mod.parse_parent_technique_from_issue(body), ("DFT-1049", None))

    def test_export_temp_id_ignored(self):
        body = issue_body(export_parent="DFT-temp-0003")
        self.assertEqual(mod.parse_parent_technique_from_issue(body), (None, None))

    def test_invalid_form_value(self):
        parent, warning = mod.parse_parent_technique_from_issue(issue_body("the decode one"))
        self.assertIsNone(parent)
        self.assertIn("not a valid technique ID", warning)


class TestUpdateParentSubtechniques(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, "data", "techniques"))
        self.parent = os.path.join(self.root, "data", "techniques", "DFT-1205.json")
        with open(self.parent, "w") as f:
            json.dump({"id": "DFT-1205", "subtechniques": []}, f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_adds_subtechnique(self):
        path, warning = mod.update_parent_subtechniques(self.root, "DFT-1205", "DFT-1206")
        self.assertEqual(path, self.parent)
        self.assertIsNone(warning)
        with open(self.parent) as f:
            self.assertEqual(json.load(f)["subtechniques"], ["DFT-1206"])

    def test_already_present(self):
        mod.update_parent_subtechniques(self.root, "DFT-1205", "DFT-1206")
        self.assertEqual(mod.update_parent_subtechniques(self.root, "DFT-1205", "DFT-1206"),
                         (None, None))

    def test_missing_parent(self):
        path, warning = mod.update_parent_subtechniques(self.root, "DFT-9999", "DFT-1206")
        self.assertIsNone(path)
        self.assertIn("not found", warning)


if __name__ == "__main__":
    unittest.main()
