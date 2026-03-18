"""
Parses a GitHub issue created from the 'Propose New Reference' template
and checks it against the existing reference corpus.

Used by the GitHub Action to post a comment indicating whether the reference
already exists or needs to be created.

Usage:
    python3 admin/issue_parsers/parse_reference_issue.py --issue-body-file issue_body.md
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body
from solve_it_library.reference_matching import (
    load_reference_corpus,
    match_reference,
    get_next_dfcite_id,
)


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

    if result:
        cite_id, match_type = result
        existing_text = corpus.get(cite_id, "")
        lines.append(f"This reference appears to match an existing citation: **{cite_id}**")
        lines.append("")
        lines.append(f"> {existing_text[:300]}{'...' if len(existing_text) > 300 else ''}")
        lines.append("")
        lines.append(f"Match type: {match_type}")
        lines.append("")
        lines.append("If this is indeed the same reference, no new citation file is needed — "
                      f"just use `{cite_id}` when referencing it in techniques, weaknesses, or mitigations.")
    else:
        next_id = get_next_dfcite_id(project_root)
        lines.append(f"No existing match found. A new reference can be assigned: **{next_id}**")
        lines.append("")
        lines.append("To add this reference, create the following file(s):")
        lines.append("")
        lines.append(f"**`data/references/{next_id}.txt`**")
        lines.append("```")
        lines.append(citation_text)
        lines.append("```")
        if bibtex:
            lines.append("")
            lines.append(f"**`data/references/{next_id}.bib`**")
            lines.append("```bibtex")
            lines.append(bibtex)
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
