"""
Test that parse_reference_issue.py includes the REFERENCE_PREVIEW marker.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parse_reference_issue import build_comment


class TestReferencePreviewMarker(unittest.TestCase):
    """Verify the REFERENCE_PREVIEW HTML comment is present in output."""

    def _project_root(self):
        return os.path.join(os.path.dirname(__file__), '..')

    def test_marker_present_for_new_reference(self):
        fields = {
            "Citation text": "Smith, J. (2099), A totally unique test reference for unit testing.",
            "BibTeX entry": "_No response_",
        }
        comment = build_comment(fields, self._project_root())
        self.assertIn("<!-- REFERENCE_PREVIEW -->", comment)
        # Marker should be at the very start
        self.assertTrue(comment.startswith("<!-- REFERENCE_PREVIEW -->"))

    def test_marker_present_for_matched_reference(self):
        fields = {
            "Citation text": "DFCite-1003",
            "BibTeX entry": "_No response_",
        }
        comment = build_comment(fields, self._project_root())
        self.assertIn("<!-- REFERENCE_PREVIEW -->", comment)
        self.assertTrue(comment.startswith("<!-- REFERENCE_PREVIEW -->"))


if __name__ == "__main__":
    unittest.main()
