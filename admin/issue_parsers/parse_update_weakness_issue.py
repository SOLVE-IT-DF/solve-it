"""
Parses a GitHub issue created from the 'Update Weakness (Form)' template
and generates a BEFORE/AFTER comparison comment.

Loads the existing weakness from the knowledge base, applies proposed changes,
and posts a summary of what would change.

Usage:
    python3 admin/parse_update_weakness_issue.py --issue-body-file issue_body.md
"""

import argparse
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body, lines_to_list
from parse_weakness_issue import build_mitigation_link
from update_utils import is_no_response, build_error_comment, build_update_comment
from solve_it_library import KnowledgeBase


BROWSE_URL = "https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/weaknesses"
# Canonical ASTM codes (with hyphens, as used in the form checkboxes)
ASTM_CLASSES = ["INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT"]


def _astm_key(code, current_dict):
    """
    Return the key to use for an ASTM code in the weakness dict.

    The KnowledgeBase may return keys with underscores (INAC_EX) or hyphens
    (INAC-EX). We match whichever format already exists in the dict.
    """
    if code in current_dict:
        return code
    alt = code.replace("-", "_")
    if alt in current_dict:
        return alt
    # Default to hyphenated form
    return code


def parse_astm_checkboxes(raw_text):
    """
    Parse ASTM checkbox selections from the issue body.

    Returns None if no boxes are checked (meaning "no change"),
    or a set of checked ASTM class codes (hyphenated form).
    """
    checked = set()
    for line in raw_text.split('\n'):
        line = line.strip()
        if line.startswith("- [X]") or line.startswith("- [x]"):
            value = line.split("]", 1)[1].strip()
            code = value.split(" - ")[0].strip().split(":")[0].strip()
            if code in ASTM_CLASSES:
                checked.add(code)
    return checked if checked else None


def apply_updates(current, fields):
    """Apply form field values to a copy of the current weakness JSON."""
    updated = copy.deepcopy(current)

    # Scalar fields
    name = fields.get("New weakness name", "")
    if not is_no_response(name):
        updated["name"] = name.strip()

    # ASTM checkboxes — None means no change, empty set means all cleared
    astm_raw = fields.get("ASTM error classes", "")
    checked = parse_astm_checkboxes(astm_raw)
    if checked is not None:
        for cls in ASTM_CLASSES:
            key = _astm_key(cls, updated)
            updated[key] = "x" if cls in checked else ""

    # List fields
    mitigations = fields.get("Mitigation IDs", "")
    if not is_no_response(mitigations):
        updated["mitigations"] = lines_to_list(mitigations)

    references = fields.get("References", "")
    if not is_no_response(references):
        updated["references"] = lines_to_list(references)

    return updated


def main():
    parser = argparse.ArgumentParser(description="Parse an update weakness issue form")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--issue-body', type=str, help="Issue body as a string")
    group.add_argument('--issue-body-file', type=str, help="File containing the issue body")
    parser.add_argument('--output', type=str, help="Output file for the comment (default: stdout)")
    args = parser.parse_args()

    if args.issue_body_file:
        with open(args.issue_body_file) as f:
            body = f.read()
    else:
        body = args.issue_body

    fields = parse_issue_body(body)

    # Validate weakness ID
    weakness_id = fields.get("Weakness ID", "").strip()
    if not re.match(r'^W\d+$', weakness_id):
        print(f"Error: Invalid weakness ID format: '{weakness_id}'", file=sys.stderr)
        sys.exit(1)

    # Load from knowledge base
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')
    current = kb.get_weakness(weakness_id)

    if current is None:
        comment = build_error_comment("Weakness", weakness_id, BROWSE_URL)
    else:
        updated = apply_updates(current, fields)
        comment = build_update_comment(
            "Weakness", weakness_id, current.get("name", ""), current, updated
        )

        # Proposed new mitigations — generate pre-filled links
        new_mitigations = lines_to_list(fields.get("Propose new mitigations", ""))
        if new_mitigations:
            lines = []
            lines.append("")
            lines.append(f"### Proposed new mitigations ({len(new_mitigations)})")
            lines.append("")
            lines.append("The following new mitigations were proposed. Click each link to open a pre-filled form:")
            lines.append("")
            for m in new_mitigations:
                url = build_mitigation_link(m, weakness_id=weakness_id)
                lines.append(f"- [Create mitigation: {m}]({url})")
            comment += '\n'.join(lines)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
