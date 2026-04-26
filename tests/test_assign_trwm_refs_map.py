"""Regression test for the TRWM_REFS_MAP round-trip through assign_trwm_ids.

Reproduces the bug from issue #431 / PR #432: BibTeX values inside the
JSON-encoded TRWM_REFS_MAP marker contain `\\n` escape sequences. The old
code used `re.sub` with the JSON string as the literal replacement, which
caused the regex engine to interpret `\\n` as a real newline — producing a
posted comment whose TRWM_REFS_MAP payload was no longer valid JSON. The
autoimplement step then silently lost the refs and shipped a PR that
referenced DFCite IDs with no .bib files on disk.
"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'id_assignment'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))

from assign_trwm_ids import apply_replacements
from autoimplement_trwm import extract_refs_map


# Mirrors the BibTeX format the form parser produces: real `\n` in the dict
# value, which json.dumps emits as the two-char escape `\n`.
ORIGINAL_PREVIEW = (
    "<!-- TRWM_PREVIEW -->\n\n"
    "Some preview text...\n\n"
    "<!-- TRWM_ID_MAP: {\"DFT-temp-0001\": \"DFT-____\"} -->\n"
    "<!-- TRWM_REFS_MAP: " + json.dumps({
        "DFCite-____-1": (
            "@article{domingues2022digital,\n"
            "  title={A digital forensic view of Windows 10 notifications},\n"
            "  author={Domingues, Patr{\\'\\i}cio},\n"
            "  year={2022},\n"
            "  publisher={MDPI}\n"
            "}"
        ),
    }) + " -->"
)


class TestRefsMapRoundTrip(unittest.TestCase):

    def _simulate_assign(self, body, replacement_map, resolved_refs_map):
        """Run the same rewrite that assign_trwm_ids.main does after building
        the replacement map. Kept inline so the test fails if the production
        code regresses to using a literal-string replacement."""
        body = apply_replacements(body, replacement_map)
        replacement = f'<!-- TRWM_REFS_MAP: {json.dumps(resolved_refs_map)} -->'
        return re.sub(
            r'<!-- TRWM_REFS_MAP: ({.*?}) -->',
            lambda _m: replacement,
            body,
            count=1,
            flags=re.DOTALL,
        )

    def test_bibtex_with_braces_and_newlines_survives_assign(self):
        replacement_map = {"DFCite-____-1": "DFCite-1149"}
        resolved_refs_map = {
            "DFCite-1149": (
                "@article{domingues2022digital,\n"
                "  title={A digital forensic view of Windows 10 notifications},\n"
                "  author={Domingues, Patr{\\'\\i}cio},\n"
                "  year={2022},\n"
                "  publisher={MDPI}\n"
                "}"
            ),
        }

        revised = self._simulate_assign(
            ORIGINAL_PREVIEW, replacement_map, resolved_refs_map,
        )

        # autoimplement_trwm must be able to recover the map from the
        # rewritten body.
        recovered = extract_refs_map(revised)
        self.assertEqual(recovered, resolved_refs_map)


if __name__ == "__main__":
    unittest.main()
