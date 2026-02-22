"""
Parses a GitHub issue created from the 'Update Mitigation (Form)' template
and generates a BEFORE/AFTER comparison comment.

Loads the existing mitigation from the knowledge base, applies proposed changes,
and posts a summary of what would change.

Usage:
    python3 admin/parse_update_mitigation_issue.py --issue-body-file issue_body.md
"""

import argparse
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parse_technique_issue import parse_issue_body, lines_to_list
from update_utils import is_no_response, build_error_comment, build_update_comment
from solve_it_library import KnowledgeBase


BROWSE_URL = "https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/mitigations"


def apply_updates(current, fields):
    """Apply form field values to a copy of the current mitigation JSON."""
    updated = copy.deepcopy(current)

    # Scalar fields
    name = fields.get("New mitigation name", "")
    if not is_no_response(name):
        updated["name"] = name.strip()

    # Linked technique — uses dropdown to disambiguate no-change vs remove
    action = fields.get("Linked technique action", "No change").strip()
    if action.startswith("Set new value"):
        technique_id = fields.get("Linked technique ID", "").strip()
        if technique_id and technique_id != "_No response_":
            updated["technique"] = technique_id
    elif action.startswith("Remove current link"):
        updated.pop("technique", None)

    # List fields
    references = fields.get("References", "")
    if not is_no_response(references):
        updated["references"] = lines_to_list(references)

    return updated


def main():
    parser = argparse.ArgumentParser(description="Parse an update mitigation issue form")
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

    # Validate mitigation ID
    mitigation_id = fields.get("Mitigation ID", "").strip()
    if not re.match(r'^M\d+$', mitigation_id):
        print(f"Error: Invalid mitigation ID format: '{mitigation_id}'", file=sys.stderr)
        sys.exit(1)

    # Load from knowledge base
    base_path = os.path.join(os.path.dirname(__file__), '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')
    current = kb.get_mitigation(mitigation_id)

    if current is None:
        comment = build_error_comment("Mitigation", mitigation_id, BROWSE_URL)
    else:
        updated = apply_updates(current, fields)
        comment = build_update_comment(
            "Mitigation", mitigation_id, current.get("name", ""), current, updated
        )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
