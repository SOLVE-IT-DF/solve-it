"""
Parses a GitHub issue created from the 'Update Technique (Form)' template
and generates a BEFORE/AFTER comparison comment.

Loads the existing technique from the knowledge base, applies proposed changes,
and posts a summary of what would change.

Usage:
    python3 admin/parse_update_technique_issue.py --issue-body-file issue_body.md
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


BROWSE_URL = "https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/techniques"


def apply_updates(current, fields):
    """Apply form field values to a copy of the current technique JSON."""
    updated = copy.deepcopy(current)

    # Scalar fields — only update if the user provided a value
    name = fields.get("New technique name", "")
    if not is_no_response(name):
        updated["name"] = name.strip()

    description = fields.get("New description", "")
    if not is_no_response(description):
        updated["description"] = description.strip()

    details = fields.get("New details", "")
    if not is_no_response(details):
        updated["details"] = details.strip()

    # List fields — populated means replace entire list
    synonyms = fields.get("Synonyms", "")
    if not is_no_response(synonyms):
        updated["synonyms"] = lines_to_list(synonyms)

    examples = fields.get("Examples", "")
    if not is_no_response(examples):
        updated["examples"] = lines_to_list(examples)

    weaknesses = fields.get("Weakness IDs", "")
    if not is_no_response(weaknesses):
        updated["weaknesses"] = lines_to_list(weaknesses)

    case_input = fields.get("CASE input classes", "")
    if not is_no_response(case_input):
        updated["CASE_input_classes"] = lines_to_list(case_input)

    case_output = fields.get("CASE output classes", "")
    if not is_no_response(case_output):
        updated["CASE_output_classes"] = lines_to_list(case_output)

    references = fields.get("References", "")
    if not is_no_response(references):
        updated["references"] = lines_to_list(references)

    return updated


def main():
    parser = argparse.ArgumentParser(description="Parse an update technique issue form")
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

    # Validate technique ID
    technique_id = fields.get("Technique ID", "").strip()
    if not re.match(r'^T\d+$', technique_id):
        print(f"Error: Invalid technique ID format: '{technique_id}'", file=sys.stderr)
        sys.exit(1)

    # Load from knowledge base
    base_path = os.path.join(os.path.dirname(__file__), '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')
    current = kb.get_technique(technique_id)

    if current is None:
        comment = build_error_comment("Technique", technique_id, BROWSE_URL)
    else:
        updated = apply_updates(current, fields)
        comment = build_update_comment(
            "Technique", technique_id, current.get("name", ""), current, updated
        )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
