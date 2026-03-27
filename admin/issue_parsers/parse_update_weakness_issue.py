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
from parse_weakness_issue import build_mitigation_link, parse_categories
from update_utils import is_no_response, build_error_comment, build_update_comment
from solve_it_library import KnowledgeBase
from solve_it_library.models import VALID_WEAKNESS_CLASSES
from solve_it_library.reference_matching import process_reference_lines


BROWSE_URL = "https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/weaknesses"


def apply_updates(current, fields, project_root=None):
    """Apply form field values to a copy of the current weakness JSON.

    Returns (updated_dict, match_report, new_citations).
    """
    updated = copy.deepcopy(current)
    match_report = []
    new_citations = []
    ref_warnings = []

    # Scalar fields
    name = fields.get("New weakness name", "")
    if not is_no_response(name):
        updated["name"] = name.strip()

    description = fields.get("New description", "")
    if not is_no_response(description):
        updated["description"] = description.strip()

    # Categories — blank means no change
    classes_raw = fields.get("Categories", "")
    if not is_no_response(classes_raw):
        valid_classes, invalid_classes = parse_categories(classes_raw)
        if invalid_classes:
            valid_list = ", ".join(sorted(VALID_WEAKNESS_CLASSES))
            errors = [f"Unrecognised weakness class `{bad}`" for bad in invalid_classes]
            errors.append(f"Valid classes: `{valid_list}`")
            return None, [], [], errors
        updated["categories"] = valid_classes

    # List fields
    mitigations = fields.get("Mitigation IDs", "")
    if not is_no_response(mitigations):
        updated["mitigations"] = lines_to_list(mitigations)

    references = fields.get("References", "")
    if not is_no_response(references):
        ref_lines = lines_to_list(references)
        if ref_lines and project_root:
            processed_refs, match_report, new_citations, ref_warnings = process_reference_lines(ref_lines, project_root)
            updated["references"] = processed_refs
        else:
            updated["references"] = []

    return updated, match_report, new_citations, ref_warnings


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
    if not re.match(r'^DFW-\d{4,6}$', weakness_id):
        print(f"Error: Invalid weakness ID format: '{weakness_id}'", file=sys.stderr)
        sys.exit(1)

    # Load from knowledge base
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')
    current = kb.get_weakness(weakness_id)

    if current is None:
        comment = build_error_comment("Weakness", weakness_id, BROWSE_URL)
    else:
        updated, match_report, new_citations, ref_warnings = apply_updates(current, fields, base_path)

        if updated is None:
            # Validation failure (e.g. invalid weakness classes)
            lines = [
                f"**Error:** Could not update weakness `{weakness_id}`.",
                "",
            ]
            for err in ref_warnings:
                lines.append(f"- {err}")
            lines.append("")
            lines.append("Please fix the errors and resubmit.")
            lines.append("")
            lines.append("---")
            lines.append("*This comment was automatically generated from the update form.*")
            comment = '\n'.join(lines)
        else:
            comment = build_update_comment(
                "Weakness", weakness_id, current.get("name", ""), current, updated
            )

            # Reference warnings
            if ref_warnings:
                warn_lines = ["", "### :warning: Reference warnings", ""]
                for w in ref_warnings:
                    warn_lines.append(f"- {w}")
                comment += '\n'.join(warn_lines)

        # References match report
        if match_report:
            ref_lines = ["", "### References", "",
                         "The following references were checked:", ""]
            ref_lines.extend(match_report)
            comment += '\n'.join(ref_lines)

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
                lines.append(f"- [`{m}`]({url})")
            comment += '\n'.join(lines)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
