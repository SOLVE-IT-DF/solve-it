"""
Parses a GitHub issue created from the 'Update DFCite Relevance Summary' template
and generates a preview comment showing the proposed change.

Usage:
    python3 admin/issue_parsers/parse_update_dfcite_relevance_issue.py \
        --issue-body-file issue_body.md --output comment.md
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body
from solve_it_library import KnowledgeBase
from solve_it_library.reference_matching import load_reference_corpus


ITEM_ID_RE = re.compile(r'^(DFT|DFW|DFM)-\d{4,6}$')
PREFIX_TO_TYPE = {"DFT": "technique", "DFW": "weakness", "DFM": "mitigation"}
DFCITE_RE = re.compile(r'^DFCite-\d{4,6}$')


def main():
    parser = argparse.ArgumentParser(
        description="Parse an update DFCite relevance issue form"
    )
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

    # Validate item ID and derive type from prefix
    item_id = fields.get("Item ID", "").strip()
    if not ITEM_ID_RE.match(item_id):
        print(f"Error: Invalid item ID format: '{item_id}'. "
              "Expected DFT-XXXX, DFW-XXXX, or DFM-XXXX", file=sys.stderr)
        sys.exit(1)
    item_type = PREFIX_TO_TYPE[item_id.split("-")[0]]

    # Validate DFCite ID
    dfcite_id = fields.get("DFCite ID", "").strip()
    if not DFCITE_RE.match(dfcite_id):
        print(f"Error: Invalid DFCite ID format: '{dfcite_id}'. "
              "Expected DFCite-XXXX", file=sys.stderr)
        sys.exit(1)

    # Validate relevance summary length
    relevance_summary = fields.get("Relevance Summary", "").strip()
    if len(relevance_summary) > 280:
        print(f"Error: Relevance summary is {len(relevance_summary)} characters "
              "(max 280)", file=sys.stderr)
        sys.exit(1)

    if not relevance_summary:
        print("Error: Relevance summary is empty", file=sys.stderr)
        sys.exit(1)

    # Load from knowledge base
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    getter = {
        "technique": kb.get_technique,
        "weakness": kb.get_weakness,
        "mitigation": kb.get_mitigation,
    }[item_type]

    item = getter(item_id)
    if item is None:
        type_plural = {"technique": "techniques", "weakness": "weaknesses",
                       "mitigation": "mitigations"}[item_type]
        browse_url = f"https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/{type_plural}"
        comment = (
            f"**Error:** {item_type.title()} `{item_id}` was not found in the knowledge base.\n\n"
            f"Please check the ID and try again. "
            f"You can browse existing {type_plural} [here]({browse_url}).\n\n"
            "---\n"
            "*This comment was automatically generated from the update form.*"
        )
        _write_output(comment, args.output)
        return

    # Find the matching reference
    references = item.get("references", [])
    matching_ref = None
    for ref in references:
        if isinstance(ref, dict) and ref.get("DFCite_id") == dfcite_id:
            matching_ref = ref
            break

    if matching_ref is None:
        comment = (
            f"**Error:** Reference `{dfcite_id}` was not found in "
            f"`{item_id}` ({item.get('name', '')}).\n\n"
            f"The item has {len(references)} reference(s). "
            "Please check the DFCite ID and try again.\n\n"
            "---\n"
            "*This comment was automatically generated from the update form.*"
        )
        _write_output(comment, args.output)
        return

    # Build preview comment
    current_relevance = matching_ref.get("relevance_summary_280", "")
    item_name = item.get("name", "")

    # Look up citation text
    ref_corpus = load_reference_corpus(base_path)
    citation_text = ref_corpus.get(dfcite_id, "")

    lines = []
    lines.append("<!-- DFCITE_RELEVANCE_UPDATE -->")
    lines.append(f"## Update DFCite relevance: {dfcite_id} in {item_id}")
    lines.append("")
    lines.append(f"**Item:** `{item_id}` — {item_name}")
    if citation_text:
        lines.append(f"**Reference:** `{dfcite_id}` — {citation_text}")
    else:
        lines.append(f"**Reference:** `{dfcite_id}`")
    lines.append("")
    lines.append("### Current relevance summary")
    lines.append("")
    if current_relevance:
        lines.append(f"> {current_relevance}")
    else:
        lines.append("> *(none)*")
    lines.append("")
    lines.append("### Proposed relevance summary")
    lines.append("")
    lines.append(f"> {relevance_summary}")
    lines.append("")
    lines.append(f"*{len(relevance_summary)} / 280 characters*")
    lines.append("")
    lines.append("### Data")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps({
        "item_type": item_type,
        "item_id": item_id,
        "dfcite_id": dfcite_id,
        "relevance_summary_280": relevance_summary,
    }, indent=4))
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("*This comment was automatically generated from the update form.*")

    comment = '\n'.join(lines)
    _write_output(comment, args.output)


def _write_output(comment, output_path):
    if output_path:
        with open(output_path, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
