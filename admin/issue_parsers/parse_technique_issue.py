"""
Parses a GitHub issue created from the 'Propose New Technique (Form)' template
and generates a JSON representation of the technique.

Used by the GitHub Action to post a comment with the proposed JSON.

Usage:
    python3 admin/parse_technique_issue.py --issue-body "$(cat issue_body.md)"
    python3 admin/parse_technique_issue.py --issue-body-file issue_body.md
"""

import argparse
import json
import re
import sys


def parse_issue_body(body):
    """
    Parse a GitHub issue form body into a dict of field values.

    GitHub issue forms produce markdown like:
        ### Field Label

        ```text
        content here
        ```

    or for non-render fields:
        ### Field Label

        content here
    """
    fields = {}
    current_label = None
    current_lines = []
    in_code_block = False

    for line in body.split('\n'):
        # Detect heading (new field)
        heading_match = re.match(r'^### (.+)$', line.strip())
        if heading_match and not in_code_block:
            # Save previous field
            if current_label is not None:
                fields[current_label] = '\n'.join(current_lines).strip()
            current_label = heading_match.group(1).strip()
            current_lines = []
            continue

        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue

        if current_label is not None:
            current_lines.append(line)

    # Save last field
    if current_label is not None:
        fields[current_label] = '\n'.join(current_lines).strip()

    return fields


def lines_to_list(text):
    """Split text into a list of non-empty lines."""
    if not text or text == '_No response_':
        return []
    return [line.strip() for line in text.strip().split('\n') if line.strip()]


def build_technique_json(fields):
    """Build a SOLVE-IT technique JSON dict from parsed form fields."""
    technique = {
        "id": "T____",
        "name": fields.get("Technique name", ""),
        "description": fields.get("Description", ""),
        "synonyms": lines_to_list(fields.get("Synonyms", "")),
        "details": fields.get("Details", "") if fields.get("Details", "") != "_No response_" else "",
        "subtechniques": [],
        "examples": lines_to_list(fields.get("Examples", "")),
        "weaknesses": lines_to_list(fields.get("Existing weakness IDs", "")),
        "CASE_input_classes": lines_to_list(fields.get("CASE input classes", "")),
        "CASE_output_classes": lines_to_list(fields.get("CASE output classes", "")),
        "references": lines_to_list(fields.get("References", "")),
    }
    return technique


def build_comment(technique, fields):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("Thanks for proposing a new technique! Here's what it would look like as JSON:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(technique, indent=4))
    lines.append("```")

    lines.append("\n---")
    lines.append("*This comment was automatically generated. The technique ID (T____) will be assigned during review.*")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse a technique issue form and generate JSON")
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
    technique = build_technique_json(fields)
    comment = build_comment(technique, fields)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
