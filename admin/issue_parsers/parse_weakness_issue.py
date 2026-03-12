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
import os
import sys
from urllib.parse import quote, urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from parse_technique_issue import parse_issue_body, lines_to_list
from solve_it_library.reference_matching import process_reference_lines


ASTM_CLASSES = ["INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT"]


def build_weakness_json(fields, project_root=None):
    """Build a SOLVE-IT weakness JSON dict from parsed form fields.

    Returns (weakness_dict, match_report, new_citations).
    """
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

    ref_lines = lines_to_list(fields.get("References", ""))
    if ref_lines and project_root:
        processed_refs, match_report, new_citations = process_reference_lines(ref_lines, project_root)
    else:
        processed_refs = []
        match_report = []
        new_citations = []

    weakness = {
        "id": "DFW-____",
        "name": fields.get("Weakness name", ""),
    }

    for cls in ASTM_CLASSES:
        weakness[cls] = "x" if cls in checked else ""

    weakness["mitigations"] = lines_to_list(fields.get("Existing mitigation IDs", ""))
    weakness["references"] = processed_refs

    return weakness, match_report, new_citations


REPO_URL = "https://github.com/SOLVE-IT-DF/solve-it"
MITIGATION_TEMPLATE = "1c_propose-new-mitigation-form.yml"


def build_mitigation_link(name, weakness_id=None):
    """Build a pre-filled URL for the 'Propose New Mitigation' issue form."""
    params = {"template": MITIGATION_TEMPLATE, "mitigation-name": name}
    if weakness_id:
        params["existing-weaknesses"] = weakness_id
    return f"{REPO_URL}/issues/new?{urlencode(params, quote_via=quote)}"


def build_comment(weakness, fields, match_report=None, new_citations=None):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("Thanks for proposing a new weakness! Here's what it would look like as JSON:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(weakness, indent=4))
    lines.append("```")

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

    # Relevant techniques — remind user to link the weakness back
    relevant_techniques = lines_to_list(fields.get("Techniques this applies to", ""))
    if relevant_techniques:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"### Relevant techniques ({len(relevant_techniques)})")
        lines.append("")
        lines.append("Once this weakness has been assigned an ID, you will also need to add it to the following techniques:")
        lines.append("")
        for t in relevant_techniques:
            lines.append(f"- Add your new weakness ID (DFW-____) to Technique **{t}**")

    lines.append("\n---")
    lines.append("*This comment was automatically generated. The weakness ID (DFW-____) will be assigned during review.*")

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
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    weakness, match_report, new_citations = build_weakness_json(fields, project_root)
    comment = build_comment(weakness, fields, match_report, new_citations)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
