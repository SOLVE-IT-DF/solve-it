"""
Parses a GitHub issue created from the 'Propose New Weakness (Form)' template
and generates a JSON representation of the weakness.

Used by the GitHub Action to post a comment with the proposed JSON.

Usage:
    python3 admin/parse_weakness_issue.py --issue-body "$(cat issue_body.md)"
    python3 admin/parse_weakness_issue.py --issue-body-file issue_body.md
"""

import argparse
import json
import sys
from urllib.parse import quote, urlencode

from parse_technique_issue import parse_issue_body, lines_to_list


ASTM_CLASSES = ["INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT"]


def build_weakness_json(fields):
    """Build a SOLVE-IT weakness JSON dict from parsed form fields."""
    # Parse ASTM error classes from checkboxes
    # GitHub checkboxes produce lines like "- [X] INCOMP" or "- [ ] INAC-EX"
    astm_raw = fields.get("ASTM error classes", "")
    checked = set()
    for line in astm_raw.split('\n'):
        line = line.strip()
        if line.startswith("- [X]") or line.startswith("- [x]"):
            value = line.split("]", 1)[1].strip()
            # Extract just the code (before any description)
            code = value.split(" - ")[0].strip().split(":")[0].strip()
            if code in ASTM_CLASSES:
                checked.add(code)

    weakness = {
        "id": "W____",
        "name": fields.get("Weakness name", ""),
    }

    for cls in ASTM_CLASSES:
        weakness[cls] = "x" if cls in checked else ""

    weakness["mitigations"] = lines_to_list(fields.get("Existing mitigation IDs", ""))
    weakness["references"] = lines_to_list(fields.get("References", ""))

    return weakness


REPO_URL = "https://github.com/SOLVE-IT-DF/solve-it"
MITIGATION_TEMPLATE = "1c_propose-new-mitigation-form.yml"


def build_mitigation_link(name, weakness_id=None):
    """Build a pre-filled URL for the 'Propose New Mitigation' issue form."""
    params = {"template": MITIGATION_TEMPLATE, "mitigation-name": name}
    if weakness_id:
        params["existing-weaknesses"] = weakness_id
    return f"{REPO_URL}/issues/new?{urlencode(params, quote_via=quote)}"


def build_comment(weakness, fields):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("Thanks for proposing a new weakness! Here's what it would look like as JSON:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(weakness, indent=4))
    lines.append("```")

    # Proposed new mitigations — generate pre-filled links
    new_mitigations = lines_to_list(fields.get("Propose new mitigations", ""))
    if new_mitigations:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"### Proposed new mitigations ({len(new_mitigations)})")
        lines.append("")
        lines.append("The following new mitigations were proposed. Click each link to open a pre-filled form:")
        lines.append("")
        for m in new_mitigations:
            url = build_mitigation_link(m)
            lines.append(f"- [Create mitigation: {m}]({url})")

    lines.append("\n---")
    lines.append("*This comment was automatically generated. The weakness ID (W____) will be assigned during review.*")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse a weakness issue form and generate JSON")
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
    weakness = build_weakness_json(fields)
    comment = build_comment(weakness, fields)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
