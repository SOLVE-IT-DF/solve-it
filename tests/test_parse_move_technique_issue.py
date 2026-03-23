"""Tests for admin/issue_parsers/parse_move_technique_issue.py."""

import subprocess
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_move_technique_issue import (
    find_current_parent,
    find_current_objectives,
    build_move_comment,
)

# Path to the parser script for integration tests
PARSER_SCRIPT = os.path.join(
    os.path.dirname(__file__), '..', 'admin', 'issue_parsers', 'parse_move_technique_issue.py'
)


def make_issue_body(technique_id, destination, rationale="Test rationale"):
    """Build a mock GitHub issue body matching the move technique form."""
    return (
        f"### Technique to move\n\n{technique_id}\n\n"
        f"### Destination\n\n{destination}\n\n"
        f"### Rationale\n\n```text\n{rationale}\n```\n\n"
        f"### Any other notes\n\n_No response_"
    )


class TestBuildMoveComment(unittest.TestCase):

    def test_contains_move_type(self):
        comment = build_move_comment(
            "DFT-1001", "Triage", "DFO-1010", "DFO-1010 (Preserve digital evidence)",
            "Move technique to a different objective",
            "Move `DFT-1001` (Triage) from X to Y.",
            ["Remove from X", "Add to Y"],
        )
        self.assertIn("**Move type:** Move technique to a different objective", comment)

    def test_contains_changes(self):
        comment = build_move_comment(
            "DFT-1001", "Triage", "DFT-1010", "DFT-1010 (Some technique)",
            "Demote technique to subtechnique",
            "Demote `DFT-1001` (Triage) to subtechnique of `DFT-1010`.",
            ["Remove from objective", "Add to subtechniques"],
        )
        self.assertIn("### Changes required", comment)
        self.assertIn("- Remove from objective", comment)
        self.assertIn("- Add to subtechniques", comment)

    def test_contains_description(self):
        comment = build_move_comment(
            "DFT-1001", "Triage", "DFO-1005", "DFO-1005 (Prioritize)",
            "Promote subtechnique to top-level technique",
            "Promote `DFT-1001` (Triage) to top-level under `DFO-1005`.",
            ["Change A"],
        )
        self.assertIn("Promote `DFT-1001` (Triage) to top-level under `DFO-1005`.", comment)


class TestIntegrationMoveToObjective(unittest.TestCase):
    """Integration tests that run the parser against the real knowledge base."""

    def _run_parser(self, technique_id, destination):
        body = make_issue_body(technique_id, destination)
        result = subprocess.run(
            [sys.executable, PARSER_SCRIPT, '--issue-body', body],
            capture_output=True, text=True,
        )
        return result

    def test_move_technique_to_different_objective(self):
        result = self._run_parser("DFT-1001", "DFO-1010")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Move technique to a different objective", result.stdout)
        self.assertIn("DFT-1001", result.stdout)
        self.assertIn("DFO-1010", result.stdout)

    def test_already_at_destination(self):
        result = self._run_parser("DFT-1001", "DFO-1005")
        self.assertEqual(result.returncode, 0)
        self.assertIn("No move needed", result.stdout)

    def test_demote_to_subtechnique(self):
        result = self._run_parser("DFT-1001", "DFT-1010")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Demote technique to subtechnique", result.stdout)
        self.assertIn("subtechniques list", result.stdout)

    def test_self_reference_error(self):
        result = self._run_parser("DFT-1001", "DFT-1001")
        self.assertEqual(result.returncode, 0)
        self.assertIn("cannot be made a subtechnique of itself", result.stdout)

    def test_invalid_technique_id(self):
        result = self._run_parser("INVALID", "DFO-1010")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid technique ID", result.stderr)

    def test_invalid_destination_id(self):
        result = self._run_parser("DFT-1001", "INVALID")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid destination ID", result.stderr)

    def test_nonexistent_technique(self):
        result = self._run_parser("DFT-9999", "DFO-1010")
        self.assertEqual(result.returncode, 0)
        self.assertIn("was not found", result.stdout)

    def test_nonexistent_objective(self):
        result = self._run_parser("DFT-1001", "DFO-9999")
        self.assertEqual(result.returncode, 0)
        self.assertIn("was not found", result.stdout)

    def test_nonexistent_dest_technique(self):
        result = self._run_parser("DFT-1001", "DFT-9999")
        self.assertEqual(result.returncode, 0)
        self.assertIn("was not found", result.stdout)


class TestFindCurrentObjectives(unittest.TestCase):
    """Test find_current_objectives against real KB."""

    @classmethod
    def setUpClass(cls):
        base_path = os.path.join(os.path.dirname(__file__), '..')
        cls.kb = KnowledgeBase(base_path, 'solve-it.json')

    def test_technique_with_objective(self):
        # DFT-1001 (Triage) is under DFO-1005
        results = find_current_objectives(self.kb, "DFT-1001")
        obj_ids = [r[0] for r in results]
        self.assertIn("DFO-1005", obj_ids)

    def test_nonexistent_technique(self):
        results = find_current_objectives(self.kb, "DFT-9999")
        self.assertEqual(results, [])


# Need to import KnowledgeBase for the find_ tests
from solve_it_library import KnowledgeBase


if __name__ == '__main__':
    unittest.main()
