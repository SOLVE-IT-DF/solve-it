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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body, lines_to_list, build_weakness_link
from update_utils import is_no_response, build_error_comment, build_update_comment
from solve_it_library import KnowledgeBase
from solve_it_library.reference_matching import process_reference_lines


BROWSE_URL = "https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/techniques"


def apply_updates(current, fields, project_root=None):
    """Apply form field values to a copy of the current technique JSON.

    Returns (updated_dict, match_report, new_citations).
    """
    updated = copy.deepcopy(current)
    match_report = []
    new_citations = []
    ref_warnings = []

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

    subtechniques = fields.get("Subtechnique IDs", "")
    if not is_no_response(subtechniques):
        updated["subtechniques"] = lines_to_list(subtechniques)

    weaknesses = fields.get("Weakness IDs", "")
    if not is_no_response(weaknesses):
        updated["weaknesses"] = lines_to_list(weaknesses)

    case_input = fields.get("Ontology input classes", "")
    if not is_no_response(case_input):
        updated["CASE_input_classes"] = lines_to_list(case_input)

    case_output = fields.get("Ontology output classes", "")
    if not is_no_response(case_output):
        updated["CASE_output_classes"] = lines_to_list(case_output)

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
    if not re.match(r'^DFT-\d{4,6}$', technique_id):
        print(f"Error: Invalid technique ID format: '{technique_id}'", file=sys.stderr)
        sys.exit(1)

    # Load from knowledge base
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')
    current = kb.get_technique(technique_id)

    if current is None:
        comment = build_error_comment("Technique", technique_id, BROWSE_URL)
    else:
        updated, match_report, new_citations, ref_warnings = apply_updates(current, fields, base_path)
        comment = build_update_comment(
            "Technique", technique_id, current.get("name", ""), current, updated
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

        # Proposed new weaknesses — generate pre-filled links
        new_weaknesses = lines_to_list(fields.get("Propose new weaknesses", ""))
        if new_weaknesses:
            lines = []
            lines.append("")
            lines.append(f"### Proposed new weaknesses ({len(new_weaknesses)})")
            lines.append("")
            lines.append("The following new weaknesses were proposed. Click each link to open a pre-filled form:")
            lines.append("")
            for w in new_weaknesses:
                url = build_weakness_link(w, technique_id=technique_id)
                lines.append(f"- [`{w}`]({url})")
            comment += '\n'.join(lines)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
