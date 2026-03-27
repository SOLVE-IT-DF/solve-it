"""Tests for admin/issue_parsers/parse_update_mitigation_issue.py."""

import unittest
import copy
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_update_mitigation_issue import apply_updates


SAMPLE_MITIGATION = {
    "id": "DFM-1001",
    "name": "Test mitigation",
    "description": "Original description",
    "references": [],
}


class TestApplyUpdates(unittest.TestCase):

    def test_no_change_when_blank(self):
        fields = {
            "New mitigation name": "_No response_",
            "New description": "_No response_",
            "Linked technique action": "No change",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated, current)

    def test_update_name(self):
        fields = {
            "New mitigation name": "New name",
            "New description": "_No response_",
            "Linked technique action": "No change",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated["name"], "New name")

    def test_update_description(self):
        fields = {
            "New mitigation name": "_No response_",
            "New description": "Updated description",
            "Linked technique action": "No change",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated["description"], "Updated description")

    def test_description_no_change_when_blank(self):
        fields = {
            "New mitigation name": "_No response_",
            "New description": "_No response_",
            "Linked technique action": "No change",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated["description"], "Original description")

    def test_set_linked_technique(self):
        fields = {
            "New mitigation name": "_No response_",
            "New description": "_No response_",
            "Linked technique action": "Set new value (provide ID below)",
            "Linked technique ID": "DFT-1002",
            "References": "_No response_",
        }
        current = copy.deepcopy(SAMPLE_MITIGATION)
        updated, _, _, _ = apply_updates(current, fields)
        self.assertEqual(updated["technique"], "DFT-1002")

    def test_remove_linked_technique(self):
        current = copy.deepcopy(SAMPLE_MITIGATION)
        current["technique"] = "DFT-1001"
        fields = {
            "New mitigation name": "_No response_",
            "New description": "_No response_",
            "Linked technique action": "Remove current link",
            "References": "_No response_",
        }
        updated, _, _, _ = apply_updates(current, fields)
        self.assertNotIn("technique", updated)


if __name__ == '__main__':
    unittest.main()
