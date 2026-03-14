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
import os
import re
import sys
from urllib.parse import quote, urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from solve_it_library.reference_matching import process_reference_lines


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


def build_technique_json(fields, project_root=None):
    """Build a SOLVE-IT technique JSON dict from parsed form fields.

    Returns (technique_dict, match_report, new_citations).
    """
    ref_lines = lines_to_list(fields.get("References", ""))
    if ref_lines and project_root:
        processed_refs, match_report, new_citations = process_reference_lines(ref_lines, project_root)
    else:
        processed_refs = []
        match_report = []
        new_citations = []

    technique = {
        "id": "DFT-____",
        "name": fields.get("Technique name", ""),
        "description": fields.get("Description", ""),
        "synonyms": lines_to_list(fields.get("Synonyms", "")),
        "details": fields.get("Details", "") if fields.get("Details", "") != "_No response_" else "",
        "subtechniques": [],
        "examples": lines_to_list(fields.get("Examples", "")),
        "weaknesses": lines_to_list(fields.get("Existing weakness IDs", "")),
        "CASE_input_classes": lines_to_list(fields.get("CASE input classes", "")),
        "CASE_output_classes": lines_to_list(fields.get("CASE output classes", "")),
        "references": processed_refs,
    }
    return technique, match_report, new_citations


REPO_URL = "https://github.com/SOLVE-IT-DF/solve-it"
WEAKNESS_TEMPLATE = "1b_propose-new-weakness-form.yml"


def build_weakness_link(name, technique_id=None):
    """Build a pre-filled URL for the 'Propose New Weakness' issue form."""
    params = {"template": WEAKNESS_TEMPLATE, "weakness-name": name}
    if technique_id:
        params["relevant-techniques"] = technique_id
    return f"{REPO_URL}/issues/new?{urlencode(params, quote_via=quote)}"


def build_comment(technique, fields, match_report=None, new_citations=None):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("Thanks for proposing a new technique! Here's what it would look like as JSON:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(technique, indent=4))
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

    # Proposed new weaknesses — generate pre-filled links
    new_weaknesses = lines_to_list(fields.get("Propose new weaknesses", ""))
    if new_weaknesses:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"### Proposed new weaknesses ({len(new_weaknesses)})")
        lines.append("")
        lines.append("The following new weaknesses were proposed. Click each link to open a pre-filled form:")
        lines.append("")
        for w in new_weaknesses:
            url = build_weakness_link(w)
            lines.append(f"- [Create weakness: {w}]({url})")

    # Reminder to add technique to solve-it.json under the selected objective
    objective = fields.get("Objective", "").strip()
    if objective and objective != "_No response_" and objective != "Other (specify below)":
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("### Next steps")
        lines.append("")
        lines.append(f"Once this technique has been assigned an ID, you will also need to add it to the objective **\"{objective}\"** in `data/solve-it.json`.")
    elif objective == "Other (specify below)":
        other_objective = fields.get("Propose new objective", "").strip()
        if other_objective and other_objective != "_No response_":
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("### Next steps")
            lines.append("")
            lines.append(f"A new objective was proposed: **\"{other_objective}\"**. Once this technique has been assigned an ID, a new objective entry will need to be created in `data/solve-it.json` and the technique added to it.")

    lines.append("\n---")
    lines.append("*This comment was automatically generated. The technique ID (DFT-____) will be assigned during review.*")

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
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    technique, match_report, new_citations = build_technique_json(fields, project_root)
    comment = build_comment(technique, fields, match_report, new_citations)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
