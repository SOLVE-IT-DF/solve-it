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
import sys

from parse_technique_issue import parse_issue_body, lines_to_list


def build_mitigation_json(fields):
    """Build a SOLVE-IT mitigation JSON dict from parsed form fields."""
    mitigation = {
        "id": "M____",
        "name": fields.get("Mitigation name", ""),
    }

    technique = fields.get("Linked technique", "").strip()
    if technique and technique != "_No response_":
        mitigation["technique"] = technique

    mitigation["references"] = lines_to_list(fields.get("References", ""))

    return mitigation


def build_comment(mitigation, fields):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("Thanks for proposing a new mitigation! Here's what it would look like as JSON:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(mitigation, indent=4))
    lines.append("```")

    lines.append("\n---")
    lines.append("*This comment was automatically generated. The mitigation ID (M____) will be assigned during review.*")

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
    mitigation = build_mitigation_json(fields)
    comment = build_comment(mitigation, fields)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
