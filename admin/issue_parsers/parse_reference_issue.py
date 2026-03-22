"""
Parses a GitHub issue created from the 'Propose New Reference' template
and checks it against the existing reference corpus.

Used by the GitHub Action to post a comment indicating whether the reference
already exists or needs to be created.

Usage:
    python3 admin/issue_parsers/parse_reference_issue.py --issue-body-file issue_body.md
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body
from solve_it_library.reference_matching import (
    load_reference_corpus,
    match_reference,
)

# Valid item ID pattern for cite-in-items
VALID_ITEM_ID_RE = re.compile(r'^(DFT|DFW|DFM)-\d{4,6}$')


def parse_cite_in_items(raw_text):
    """Parse the cite-in-items field into a list of dicts.

    Each line should be: ITEM_ID | relevance summary
    Returns (items, errors) where items is a list of
    {"item_id": ..., "relevance_summary": ...} dicts.
    """
    items = []
    errors = []

    if not raw_text or raw_text.strip() in ("", "_No response_"):
        return items, errors

    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        if '|' not in line:
            errors.append(f"Missing `|` separator: `{line}`")
            continue

        item_id, relevance = line.split('|', 1)
        item_id = item_id.strip()
        relevance = relevance.strip()

        if not VALID_ITEM_ID_RE.match(item_id):
            errors.append(f"Invalid item ID format: `{item_id}`")
            continue

        if len(relevance) > 280:
            errors.append(
                f"Relevance summary for `{item_id}` exceeds 280 chars "
                f"({len(relevance)} chars)"
            )
            continue

        items.append({"item_id": item_id, "relevance_summary": relevance})

    return items, errors


def validate_cite_items_exist(cite_items, project_root):
    """Check that each cited item's JSON file exists.

    Returns (valid_items, warnings).
    """
    prefix_to_dir = {
        "DFT": "techniques",
        "DFW": "weaknesses",
        "DFM": "mitigations",
    }
    valid = []
    warnings = []

    for item in cite_items:
        item_id = item["item_id"]
        prefix = item_id.split("-")[0]
        subdir = prefix_to_dir.get(prefix)
        if subdir is None:
            warnings.append(f"Unknown prefix for `{item_id}`")
            continue

        filepath = os.path.join(project_root, "data", subdir, f"{item_id}.json")
        if os.path.exists(filepath):
            valid.append(item)
        else:
            warnings.append(f"Item `{item_id}` not found in `data/{subdir}/`")

    return valid, warnings


def build_comment(fields, project_root):
    """Build the GitHub comment markdown."""
    citation_text = fields.get("Citation text", "").strip()
    bibtex = fields.get("BibTeX entry", "").strip()
    if bibtex == "_No response_":
        bibtex = ""

    corpus = load_reference_corpus(project_root)
    result = match_reference(citation_text, corpus)

    lines = []
    lines.append("<!-- REFERENCE_PREVIEW -->")

    is_match = bool(result)

    explorer_refs_url = "https://explore.solveit-df.org/#references"

    if is_match:
        cite_id, match_type = result
        existing_text = corpus.get(cite_id, "")
        lines.append(f"This reference appears to match an existing citation: **{cite_id}**")
        lines.append("")
        lines.append(f"> {existing_text[:300]}{'...' if len(existing_text) > 300 else ''}")
        lines.append("")
        match_explanations = {
            "direct_id": "You submitted an existing DFCite ID.",
            "url": "A URL in your citation matches an existing reference.",
            "doi": "A DOI in your citation matches an existing reference.",
            "prefix": "The beginning of your citation text matches an existing reference.",
        }
        lines.append(f"Match type: `{match_type}` — {match_explanations.get(match_type, '')}")
        lines.append("")
        lines.append("If this is indeed the same reference, no new citation file is needed — "
                      f"just use `{cite_id}` when referencing it in techniques, weaknesses, or mitigations.")
        lines.append("")
        lines.append(f":mag: [Browse all references in the Explorer]({explorer_refs_url}) to verify this match.")
    else:
        placeholder = "DFCite-____"
        lines.append(f"No existing match found. A reference ID will be assigned during review.")
        lines.append("")
        lines.append(f":mag: Reviewers: [search existing references in the Explorer]({explorer_refs_url}) "
                      "to double-check for duplicates before assigning an ID.")
        lines.append("")
        lines.append("Proposed file contents:")
        lines.append("")
        lines.append(f"**`data/references/{placeholder}.txt`**")
        lines.append("```")
        lines.append(citation_text)
        lines.append("```")
        if bibtex:
            lines.append("")
            lines.append(f"**`data/references/{placeholder}.bib`**")
            lines.append("```bibtex")
            lines.append(bibtex)
            lines.append("```")

    # Cite-in-items section (only for new references, not existing matches)
    if not is_match:
        raw_cite = fields.get("Cite in items", "").strip()
        if raw_cite and raw_cite != "_No response_":
            cite_items, parse_errors = parse_cite_in_items(raw_cite)
            valid_items, exist_warnings = validate_cite_items_exist(
                cite_items, project_root
            )

            if cite_items or parse_errors:
                lines.append("")
                lines.append("<!-- CITE_IN_ITEMS -->")
                lines.append("")
                lines.append("### Cite in items")
                lines.append("")

                if parse_errors:
                    lines.append("**Warnings:**")
                    for err in parse_errors:
                        lines.append(f"- {err}")
                    lines.append("")

                if exist_warnings:
                    lines.append("**Item warnings:**")
                    for warn in exist_warnings:
                        lines.append(f"- {warn}")
                    lines.append("")

                if cite_items:
                    lines.append("| Item | Relevance summary | Status |")
                    lines.append("|---|---|---|")
                    valid_ids = {i["item_id"] for i in valid_items}
                    for item in cite_items:
                        status = "Found" if item["item_id"] in valid_ids else "Not found"
                        lines.append(
                            f"| `{item['item_id']}` "
                            f"| {item['relevance_summary']} "
                            f"| {status} |"
                        )
                    lines.append("")
                    lines.append("```json")
                    lines.append(json.dumps(cite_items, indent=2))
                    lines.append("```")

    lines.append("")
    lines.append("---")
    lines.append("*This comment was automatically generated from the reference proposal form.*")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse a reference issue form")
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
    comment = build_comment(fields, project_root)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
