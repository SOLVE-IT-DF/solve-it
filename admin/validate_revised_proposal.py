#!/usr/bin/env python3
"""
Validates a revised proposal comment on an update issue.

Triggered by a GitHub Actions workflow when someone posts a comment
containing a '### Proposed' JSON block on an update issue. Extracts the
JSON, validates it via the appropriate Pydantic model, checks DFCite
references, and posts a validation result comment.

Usage:
    python3 admin/validate_revised_proposal.py \
        --issue-number 407 --comment-body-file comment.md
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'issue_parsers'))

from autoimplement_update_item import (
    detect_item_type, extract_proposed_json, get_current_item,
    get_item_id_from_issue, normalize_ids_in_block,
)
from autoimplement_new_item import (
    get_issue, check_dfcite_existence, VALID_DFCITE_RE,
)
from update_utils import build_change_summary
from solve_it_library import KnowledgeBase
from solve_it_library.models import Technique, Weakness, Mitigation

MODEL_MAP = {
    "technique": Technique,
    "weakness": Weakness,
    "mitigation": Mitigation,
}


def main():
    parser = argparse.ArgumentParser(
        description="Validate a revised proposal comment on an update issue",
    )
    parser.add_argument(
        "--issue-number", type=int, required=True,
        help="GitHub issue number",
    )
    parser.add_argument(
        "--comment-body-file", type=str, required=True,
        help="Path to file containing the comment body",
    )
    parser.add_argument(
        "--project-root", type=str, default=None,
        help="Path to SOLVE-IT project root (default: auto-detect)",
    )
    args = parser.parse_args()

    project_root = args.project_root
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Read the comment body from file
    with open(args.comment_body_file, 'r') as f:
        comment_body = f.read()

    # Extract proposed JSON from the comment
    proposed = extract_proposed_json(comment_body)
    if proposed is None:
        print("No valid JSON found in ### Proposed block.", file=sys.stderr)
        sys.exit(0)  # Not an error — comment may not be a revision

    # Fetch the issue to detect item type and get item ID
    issue = get_issue(args.issue_number)
    item_type = detect_item_type(issue)
    if item_type is None:
        print("Could not detect item type from issue labels.", file=sys.stderr)
        sys.exit(0)

    item_id = get_item_id_from_issue(issue["body"], item_type)
    if item_id is None:
        post_comment(args.issue_number, validation_failed(
            "Could not extract item ID from the issue body."))
        return

    normalize_ids_in_block(proposed)

    # Ensure the ID matches
    proposed["id"] = item_id

    # Validate via Pydantic model
    model_class = MODEL_MAP.get(item_type)
    errors = []
    try:
        model_class.model_validate(proposed)
    except Exception as e:
        errors.append(f"Schema validation error: {e}")

    # Check DFCite references exist
    dfcite_warnings = check_dfcite_existence(proposed, project_root)
    if dfcite_warnings:
        errors.extend(dfcite_warnings)

    # Check for PENDING references
    has_pending = any(
        isinstance(r, dict) and r.get("DFCite_id") == "PENDING"
        for r in proposed.get("references", [])
    )
    if has_pending:
        errors.append("One or more references have a PENDING DFCite ID.")

    if errors:
        post_comment(args.issue_number, validation_failed(
            "\n".join(f"- {e}" for e in errors)))
        return

    # Load current item for change summary
    kb = KnowledgeBase(project_root, 'solve-it.json')
    current = get_current_item(kb, item_type, item_id)
    if current is None:
        post_comment(args.issue_number, validation_failed(
            f"{item_type.capitalize()} `{item_id}` not found in the knowledge base."))
        return

    # Round-trip through Pydantic to normalize
    normalized = model_class.model_validate(proposed).model_dump(by_alias=True)
    change_summary = build_change_summary(current, normalized)

    post_comment(args.issue_number, validation_passed(
        item_type, item_id, change_summary))


def validation_passed(item_type, item_id, change_summary):
    lines = [
        f"**Revised proposal validated** for {item_type} `{item_id}`.",
        "",
        "### Changes vs current knowledge base",
        "",
    ]
    lines.extend(change_summary)
    lines.append("")
    lines.append("This revised proposal will be used when `autoimplement` is applied.")
    lines.append("")
    lines.append("---")
    lines.append("*This comment was automatically generated.*")
    return "\n".join(lines)


def validation_failed(detail):
    lines = [
        "**Revised proposal validation failed.**",
        "",
        detail,
        "",
        "Please fix the JSON and post a new `### Proposed` comment.",
        "",
        "---",
        "*This comment was automatically generated.*",
    ]
    return "\n".join(lines)


def post_comment(issue_number, body):
    subprocess.run(
        ["gh", "issue", "comment", str(issue_number), "--body", body],
        check=True,
    )


if __name__ == "__main__":
    main()
