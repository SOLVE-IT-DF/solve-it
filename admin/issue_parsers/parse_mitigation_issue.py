"""
Parses a GitHub issue created from the 'Propose New Mitigation (Form)' template
and generates a JSON representation of the mitigation.

Used by the GitHub Action to post a comment with the proposed JSON.

Usage:
    python3 admin/parse_mitigation_issue.py --issue-body "$(cat issue_body.md)"
    python3 admin/parse_mitigation_issue.py --issue-body-file issue_body.md
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from parse_technique_issue import parse_issue_body, lines_to_list
from solve_it_library.reference_matching import process_reference_lines


def build_mitigation_json(fields, project_root=None):
    """Build a SOLVE-IT mitigation JSON dict from parsed form fields.

    Returns (mitigation_dict, match_report, new_citations).
    """
    ref_lines = lines_to_list(fields.get("References", ""))
    if ref_lines and project_root:
        processed_refs, match_report, new_citations, ref_warnings = process_reference_lines(ref_lines, project_root)
    else:
        processed_refs = []
        match_report = []
        new_citations = []
        ref_warnings = []

    mitigation = {
        "id": "DFM-____",
        "name": fields.get("Mitigation name", ""),
    }

    technique = fields.get("Linked technique", "").strip()
    if technique and technique != "_No response_":
        mitigation["technique"] = technique

    mitigation["references"] = processed_refs
    mitigation["_parent_weaknesses"] = lines_to_list(fields.get("Existing weakness IDs", ""))

    return mitigation, match_report, new_citations, ref_warnings


def build_comment(mitigation, fields, match_report=None, new_citations=None, ref_warnings=None):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("Thanks for proposing a new mitigation! Here's what it would look like as JSON:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(mitigation, indent=4))
    lines.append("```")

    # Reference warnings
    if ref_warnings:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("### :warning: Reference warnings")
        lines.append("")
        for w in ref_warnings:
            lines.append(f"- {w}")

    # References match report
    if match_report:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("### References")
        lines.append("")
        lines.append("The following references were matched/created:")
        lines.append("")
        lines.extend(match_report)
        if new_citations:
            lines.append("")
            lines.append("Please edit the `relevance_summary_280` fields (max 280 chars) when creating the PR.")

    # Relevant weaknesses — remind user to link the mitigation back
    existing_weaknesses = lines_to_list(fields.get("Existing weakness IDs", ""))
    if existing_weaknesses:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"### Relevant weaknesses ({len(existing_weaknesses)})")
        lines.append("")
        lines.append("Once this mitigation has been assigned an ID, you will also need to add it to the following weaknesses:")
        lines.append("")
        for w in existing_weaknesses:
            lines.append(f"- Add your new mitigation ID (DFM-____) to Weakness **{w}**")

    lines.append("\n---")
    lines.append("*This comment was automatically generated. The mitigation ID (DFM-____) will be assigned during review.*")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse a mitigation issue form and generate JSON")
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
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    mitigation, match_report, new_citations, ref_warnings = build_mitigation_json(fields, project_root)
    comment = build_comment(mitigation, fields, match_report, new_citations, ref_warnings)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
