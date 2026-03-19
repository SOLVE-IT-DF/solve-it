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
from solve_it_library.models import VALID_WEAKNESS_CLASSES


def parse_categories(raw_text):
    """Parse category codes from a textarea field (one code per line).

    Returns (valid_categories, invalid_entries) where:
    - valid_categories is a list of valid ASTM_* codes
    - invalid_entries is a list of unrecognised strings
    """
    classes = []
    invalid = []
    for line in raw_text.split('\n'):
        code = line.strip()
        if not code:
            continue
        if code in VALID_WEAKNESS_CLASSES:
            classes.append(code)
        else:
            invalid.append(code)
    return classes, invalid


def build_weakness_json(fields, project_root=None):
    """Build a SOLVE-IT weakness JSON dict from parsed form fields.

    Returns (weakness_dict, match_report, new_citations, ref_warnings).
    If invalid weakness classes are found, returns None for weakness_dict
    and the error details in ref_warnings.
    """
    # Parse weakness classes from textarea (one code per line)
    raw = fields.get("Categories", "")
    categories, invalid_classes = parse_categories(raw)

    # Fail on invalid weakness class codes
    if invalid_classes:
        valid_list = ", ".join(sorted(VALID_WEAKNESS_CLASSES))
        errors = [f"Unrecognised weakness class `{bad}`" for bad in invalid_classes]
        errors.append(f"Valid classes: `{valid_list}`")
        return None, [], [], errors

    ref_lines = lines_to_list(fields.get("References", ""))
    if ref_lines and project_root:
        processed_refs, match_report, new_citations, ref_warnings = process_reference_lines(ref_lines, project_root)
    else:
        processed_refs = []
        match_report = []
        new_citations = []
        ref_warnings = []

    weakness = {
        "id": "DFW-____",
        "name": fields.get("Weakness name", ""),
        "categories": categories,
        "mitigations": lines_to_list(fields.get("Existing mitigation IDs", "")),
        "references": processed_refs,
        "_parent_techniques": lines_to_list(fields.get("Techniques this applies to", "")),
    }

    return weakness, match_report, new_citations, ref_warnings


REPO_URL = "https://github.com/SOLVE-IT-DF/solve-it"
MITIGATION_TEMPLATE = "1c_propose-new-mitigation-form.yml"


def build_mitigation_link(name, weakness_id=None):
    """Build a pre-filled URL for the 'Propose New Mitigation' issue form."""
    params = {"template": MITIGATION_TEMPLATE, "mitigation-name": name}
    if weakness_id:
        params["existing-weaknesses"] = weakness_id
    return f"{REPO_URL}/issues/new?{urlencode(params, quote_via=quote)}"


def build_comment(weakness, fields, match_report=None, new_citations=None, ref_warnings=None):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("Thanks for proposing a new weakness! Here's what it would look like as JSON:")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(weakness, indent=4))
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
            lines.append("Review the `relevance_summary_280` fields (max 280 chars) in the PR — any summaries provided via the pipe delimiter have been pre-filled.")

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
            lines.append(f"- [`{m}`]({url})")

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
    weakness, match_report, new_citations, ref_warnings = build_weakness_json(fields, project_root)

    if weakness is None:
        # Invalid weakness classes — build error comment
        lines = [
            "**Error:** Invalid weakness classes in submission.",
            "",
        ]
        for err in ref_warnings:
            lines.append(f"- {err}")
        lines.append("")
        lines.append("Please fix the weakness classes and resubmit.")
        lines.append("")
        lines.append("---")
        lines.append("*This comment was automatically generated.*")
        comment = '\n'.join(lines)
    else:
        comment = build_comment(weakness, fields, match_report, new_citations, ref_warnings)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
