"""
Parses a GitHub issue created from the 'Update Reference (DFCite)' template
and generates a preview comment showing the proposed changes.

Loads the existing reference files (.txt and .bib) from the knowledge base,
compares with the proposed values, and posts a summary.

Usage:
    python3 admin/issue_parsers/parse_update_reference_issue.py \
        --issue-body-file issue_body.md --output comment.md
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body
from parse_reference_issue import parse_cite_in_items, validate_cite_items_exist
from update_utils import is_no_response
from solve_it_library.reference_matching import load_reference_corpus


DFCITE_RE = re.compile(r'^DFCite-\d{4,6}$')


def load_raw_file(path):
    """Read a file and return its stripped content, or None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read().strip()


def find_cited_by(kb, dfcite_id):
    """Find all items that cite a given DFCite ID.

    Returns (cited_by, existing_refs) where cited_by is a list of
    (type, id, name) tuples and existing_refs is a dict mapping
    item_id -> current relevance_summary_280.
    """
    existing_refs = {}
    cited_by = []
    for label, collection in [("technique", kb.techniques),
                               ("weakness", kb.weaknesses),
                               ("mitigation", kb.mitigations)]:
        for item in collection.values():
            for ref in item.get("references", []):
                if isinstance(ref, dict) and ref.get("DFCite_id") == dfcite_id:
                    cited_by.append((label, item["id"], item.get("name", "")))
                    existing_refs[item["id"]] = ref.get("relevance_summary_280", "")
    return cited_by, existing_refs


def build_comment(fields, project_root):
    """Build the preview comment for a reference update proposal.

    Args:
        fields: dict of parsed form fields (from parse_issue_body)
        project_root: path to the SOLVE-IT project root

    Returns:
        (comment_string, dfcite_id) or raises ValueError for invalid input.
    """
    dfcite_id = fields.get("DFCite ID", "").strip()
    if not DFCITE_RE.match(dfcite_id):
        raise ValueError(f"Invalid DFCite ID format: '{dfcite_id}'. Expected DFCite-XXXX")

    # Load existing files
    refs_dir = os.path.join(project_root, "data", "references")
    txt_path = os.path.join(refs_dir, f"{dfcite_id}.txt")
    bib_path = os.path.join(refs_dir, f"{dfcite_id}.bib")

    current_txt = load_raw_file(txt_path)
    current_bib = load_raw_file(bib_path)

    if current_txt is None and current_bib is None:
        explorer_url = "https://explore.solveit-df.org/#references"
        return (
            f"**Error:** Reference `{dfcite_id}` was not found in the knowledge base.\n\n"
            f"No `.txt` or `.bib` file exists for this ID. "
            f"Please check the ID and try again.\n\n"
            f":mag: [Browse existing references in the Explorer]({explorer_url})\n\n"
            "---\n"
            "*This comment was automatically generated from the update form.*"
        ), dfcite_id

    # Extract proposed changes
    new_txt = fields.get("New citation text", "").strip()
    if is_no_response(new_txt):
        new_txt = ""
    new_bib = fields.get("New BibTeX entry", "").strip()
    if is_no_response(new_bib):
        new_bib = ""

    # Build preview comment
    lines = []
    lines.append("<!-- REFERENCE_UPDATE_PREVIEW -->")
    lines.append(f"## Proposed update to {dfcite_id}")
    lines.append("")

    # Show current state
    lines.append("### Current citation text")
    lines.append("")
    if current_txt:
        lines.append(f"> {current_txt}")
    else:
        lines.append("> *(no .txt file)*")
    lines.append("")

    lines.append("### Current BibTeX")
    lines.append("")
    if current_bib:
        lines.append("```bibtex")
        lines.append(current_bib)
        lines.append("```")
    else:
        lines.append("> *(no .bib file)*")
    lines.append("")

    # Show proposed changes
    has_changes = False

    if new_txt:
        has_changes = True
        lines.append("### Proposed citation text")
        lines.append("")
        lines.append(f"> {new_txt}")
        lines.append("")
        if current_txt:
            if new_txt == current_txt:
                lines.append("*No change from current text.*")
                lines.append("")
    else:
        lines.append("### Proposed citation text")
        lines.append("")
        lines.append("*No change proposed (field left blank).*")
        lines.append("")

    if new_bib:
        has_changes = True
        lines.append("### Proposed BibTeX")
        lines.append("")
        lines.append("```bibtex")
        lines.append(new_bib)
        lines.append("```")
        lines.append("")
        if current_bib:
            if new_bib == current_bib:
                lines.append("*No change from current BibTeX.*")
                lines.append("")
    else:
        lines.append("### Proposed BibTeX")
        lines.append("")
        lines.append("*No change proposed (field left blank).*")
        lines.append("")

    if not has_changes:
        lines.append(":warning: **No changes were proposed.** "
                     "Both the citation text and BibTeX fields were left blank.")
        lines.append("")

    # Parse cite-in-items
    raw_cite = fields.get("Cite in additional items", "").strip()
    cite_items = []
    cite_parse_errors = []
    cite_exist_warnings = []
    valid_items = []
    if raw_cite and not is_no_response(raw_cite):
        cite_items, cite_parse_errors = parse_cite_in_items(raw_cite)
        if cite_items:
            valid_items, cite_exist_warnings = validate_cite_items_exist(
                cite_items, project_root
            )

    # Cited by — show which items already reference this DFCite
    from solve_it_library import KnowledgeBase
    kb = KnowledgeBase(project_root, 'solve-it.json')
    cited_by, existing_cited_by = find_cited_by(kb, dfcite_id)

    # Summary of changes
    lines.append("### Summary of changes")
    lines.append("")
    changes = []
    if new_txt and new_txt != (current_txt or ""):
        changes.append("- **Citation text**: changed")
    if new_bib and new_bib != (current_bib or ""):
        changes.append("- **BibTeX**: changed")
    if new_txt and not current_txt:
        changes.append("- **Citation text**: new `.txt` file will be created")
    if new_bib and not current_bib:
        changes.append("- **BibTeX**: new `.bib` file will be created")
    new_cite_items = [i for i in cite_items if i["item_id"] not in existing_cited_by]
    already_cited = [i for i in cite_items if i["item_id"] in existing_cited_by]
    if new_cite_items:
        changes.append(f"- **Cite in items**: add to {len(new_cite_items)} new item(s)")
    if not changes:
        lines.append("No changes detected.")
    else:
        lines.extend(changes)
    lines.append("")

    # Data block for autoimplement
    lines.append("### Data")
    lines.append("")
    lines.append("```json")
    data = {"dfcite_id": dfcite_id}
    if new_txt:
        data["new_txt"] = new_txt
    if new_bib:
        data["new_bib"] = new_bib
    if new_cite_items:
        data["cite_in_items"] = new_cite_items
    lines.append(json.dumps(data, indent=4))
    lines.append("```")
    lines.append("")

    # Cite in items section
    if cite_items or cite_parse_errors:
        lines.append("### Cite in additional items")
        lines.append("")

        if cite_parse_errors:
            lines.append("**Warnings:**")
            for err in cite_parse_errors:
                lines.append(f"- {err}")
            lines.append("")

        if cite_exist_warnings:
            lines.append("**Item warnings:**")
            for warn in cite_exist_warnings:
                lines.append(f"- {warn}")
            lines.append("")

        if already_cited:
            lines.append(f":information_source: {len(already_cited)} item(s) already cite "
                         f"this reference (will be skipped):")
            for item in already_cited:
                lines.append(f"- `{item['item_id']}` — already cited")
            lines.append("")

        if new_cite_items:
            lines.append("| Item | Relevance summary | Status |")
            lines.append("|---|---|---|")
            valid_ids = {i["item_id"] for i in valid_items}
            for item in new_cite_items:
                status = "Found" if item["item_id"] in valid_ids else "Not found"
                lines.append(
                    f"| `{item['item_id']}` "
                    f"| {item['relevance_summary']} "
                    f"| {status} |"
                )
            lines.append("")

    # Existing cited-by
    if cited_by:
        lines.append(f"### Currently cited by ({len(cited_by)} item{'s' if len(cited_by) != 1 else ''})")
        lines.append("")
        for item_type, item_id, item_name in cited_by:
            lines.append(f"- `{item_id}` — {item_name} ({item_type})")
        lines.append("")

    lines.append("---")
    lines.append("*This comment was automatically generated from the update form.*")

    return '\n'.join(lines), dfcite_id


def main():
    parser = argparse.ArgumentParser(
        description="Parse an update reference (DFCite) issue form"
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

    # Validate DFCite ID
    dfcite_id = fields.get("DFCite ID", "").strip()
    if not DFCITE_RE.match(dfcite_id):
        print(f"Error: Invalid DFCite ID format: '{dfcite_id}'. "
              "Expected DFCite-XXXX", file=sys.stderr)
        sys.exit(1)

    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    comment, _ = build_comment(fields, project_root)
    _write_output(comment, args.output)


def _write_output(comment, output_path):
    if output_path:
        with open(output_path, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
