#!/usr/bin/env python3
"""
Auto-implements an update to a technique, weakness, or mitigation by modifying
the existing data file and opening a PR.

Looks for the "Proposed" JSON block in the issue comments (posted by the
parse_update_*_issue.py scripts). If found, uses that JSON — which may have
been amended during review. Falls back to re-parsing the issue body and
applying updates directly.

Usage:
    python3 admin/autoimplement_update_item.py --issue-number 283
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'issue_parsers'))

from autoimplement_new_item import (
    run, validate_id, normalize_id, VALID_ID_RE, VALID_DFCITE_RE,
    classify_type, slugify, sanitise_git_value, get_submitter_info,
    get_issue, get_issue_comments,
    check_dfcite_existence,
    handle_old_format_references,
    post_blocked_comment_and_remove_label,
    build_reference_form_url,
)
from parse_technique_issue import parse_issue_body, lines_to_list
from parse_update_technique_issue import apply_updates as apply_technique_updates
from parse_update_weakness_issue import apply_updates as apply_weakness_updates
from parse_update_mitigation_issue import apply_updates as apply_mitigation_updates
from update_utils import is_no_response, build_change_summary
from solve_it_library import KnowledgeBase
from solve_it_library.models import Technique, Weakness, Mitigation


# Label → item type mapping
LABEL_TYPE_MAP = {
    "content: update technique": "technique",
    "content: update weakness": "weakness",
    "content: update mitigation": "mitigation",
}

# Item type → ID field label in the issue form
TYPE_ID_FIELD = {
    "technique": "Technique ID",
    "weakness": "Weakness ID",
    "mitigation": "Mitigation ID",
}

TYPE_DIR = {
    "technique": "techniques",
    "weakness": "weaknesses",
    "mitigation": "mitigations",
}


def detect_item_type(issue):
    """Detect item type from issue labels."""
    label_names = [l["name"] for l in issue.get("labels", [])]
    for label, item_type in LABEL_TYPE_MAP.items():
        if label in label_names:
            return item_type
    return None


def find_proposed_comment(comments):
    """Find the most recent comment containing a '### Proposed' JSON block.

    The update parsers post comments with BEFORE/AFTER JSON blocks.
    During review, this comment may be edited to amend the proposed changes.
    We use the most recent such comment.
    """
    for comment in reversed(comments):
        body = comment.get("body", "")
        if "### Proposed" in body:
            return comment
    return None


def extract_proposed_json(comment_body):
    """Extract the JSON block from the '### Proposed' section of a comment.

    Returns the parsed dict, or None if not found.
    """
    proposed_match = re.search(
        r'### Proposed\s*\n```json\s*\n(.*?)\n```',
        comment_body, re.DOTALL,
    )
    if proposed_match:
        try:
            return json.loads(proposed_match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def normalize_ids_in_block(block):
    """Normalize old-format IDs in the block to new format.

    Handles the item's own ID and any cross-reference IDs
    (weakness lists, mitigation lists, subtechniques, linked technique).
    """
    if "id" in block:
        normalized = normalize_id(block["id"])
        if normalized:
            block["id"] = normalized

    if "weaknesses" in block:
        block["weaknesses"] = [
            normalize_id(w) or w for w in block["weaknesses"]
        ]

    if "subtechniques" in block:
        block["subtechniques"] = [
            normalize_id(s) or s for s in block["subtechniques"]
        ]

    if "mitigations" in block:
        block["mitigations"] = [
            normalize_id(m) or m for m in block["mitigations"]
        ]

    if "technique" in block and block["technique"]:
        normalized = normalize_id(block["technique"])
        if normalized:
            block["technique"] = normalized


def get_item_id_from_issue(issue_body, item_type):
    """Extract and normalize the item ID from the issue body."""
    fields = parse_issue_body(issue_body)
    id_field = TYPE_ID_FIELD[item_type]
    raw_id = fields.get(id_field, "").strip()

    if not raw_id:
        return None

    return normalize_id(raw_id)


def apply_updates_for_type(item_type, current, fields, project_root):
    """Call the appropriate apply_updates function for the item type."""
    if item_type == "technique":
        return apply_technique_updates(current, fields, project_root)
    elif item_type == "weakness":
        return apply_weakness_updates(current, fields, project_root)
    elif item_type == "mitigation":
        return apply_mitigation_updates(current, fields, project_root)
    return None, [], [], []


def get_current_item(kb, item_type, item_id):
    """Load the current item from the knowledge base."""
    if item_type == "technique":
        return kb.get_technique(item_id)
    elif item_type == "weakness":
        return kb.get_weakness(item_id)
    elif item_type == "mitigation":
        return kb.get_mitigation(item_id)
    return None



def main():
    parser = argparse.ArgumentParser(
        description="Auto-implement an update to a technique/weakness/mitigation as a PR",
    )
    parser.add_argument(
        "--issue-number", type=int, required=True,
        help="GitHub issue number",
    )
    parser.add_argument(
        "--project-root", type=str, default=None,
        help="Path to SOLVE-IT project root (default: auto-detect)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without making changes",
    )
    args = parser.parse_args()

    project_root = args.project_root
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Fetch issue and comments
    print("Fetching issue...", file=sys.stderr)
    issue = get_issue(args.issue_number)
    comments = get_issue_comments(args.issue_number)

    # 2. Detect item type from labels
    item_type = detect_item_type(issue)
    if item_type is None:
        print("Error: could not detect item type from issue labels. "
              "Expected one of: content: update technique/weakness/mitigation",
              file=sys.stderr)
        sys.exit(1)
    print(f"Detected item type: {item_type}", file=sys.stderr)

    # 3. Get item ID from issue body
    item_id = get_item_id_from_issue(issue["body"], item_type)
    if item_id is None:
        print("Error: could not extract item ID from issue body.", file=sys.stderr)
        sys.exit(1)
    validate_id(item_id)
    print(f"Item ID: {item_id}", file=sys.stderr)

    # 4. Load current item from KB
    kb = KnowledgeBase(project_root, 'solve-it.json')
    current = get_current_item(kb, item_type, item_id)
    if current is None:
        print(f"Error: {item_type} {item_id} not found in knowledge base.", file=sys.stderr)
        sys.exit(1)

    # 5. Get proposed update — prefer comment (supports amendment), fall back to issue body
    proposed = None
    proposed_comment = find_proposed_comment(comments)

    if proposed_comment:
        proposed = extract_proposed_json(proposed_comment["body"])
        if proposed:
            print("Using proposed JSON from comment (may have been amended during review).",
                  file=sys.stderr)
            normalize_ids_in_block(proposed)

    if proposed is None:
        print("No proposed comment found, parsing issue body directly.", file=sys.stderr)
        fields = parse_issue_body(issue["body"])
        proposed, _match_report, _new_citations, _ref_warnings = apply_updates_for_type(
            item_type, current, fields, project_root)
        if proposed is None:
            print("Error: could not apply updates from issue body.", file=sys.stderr)
            sys.exit(1)
        normalize_ids_in_block(proposed)

    # Ensure the ID matches what was extracted from the issue body
    proposed["id"] = item_id

    # 5b. Handle raw string references (older proposed comments may have these)
    proposed["references"], ref_warnings, unmatched_raw_refs = handle_old_format_references(
        proposed, project_root)
    if ref_warnings:
        print("Reference warnings:", file=sys.stderr)
        for w in ref_warnings:
            print(f"  - {w}", file=sys.stderr)

    # 6. Check for actual changes
    if current == proposed:
        print("No changes detected between current and proposed.", file=sys.stderr)
        sys.exit(0)

    item_name = proposed.get("name", item_id)
    print(f"Updating {item_type}: {item_id} ({item_name})", file=sys.stderr)

    # 7. Check for PENDING references and DFCite existence
    has_pending = any(
        isinstance(r, dict) and r.get("DFCite_id") == "PENDING"
        for r in proposed.get("references", [])
    )
    dfcite_warnings = check_dfcite_existence(proposed, project_root)

    if has_pending or dfcite_warnings:
        print("Reference issues:", file=sys.stderr)
        for w in ref_warnings + dfcite_warnings:
            print(f"  - {w}", file=sys.stderr)

        if args.dry_run:
            print("\n=== DRY RUN: Would abort due to reference issues ===",
                  file=sys.stderr)
            return
        else:
            post_blocked_comment_and_remove_label(
                args.issue_number, item_id, unmatched_raw_refs, dfcite_warnings)
            return

    # 8. Get submitter info for attribution
    author_name, author_email = get_submitter_info(issue)
    print(f"Submitter: {author_name} <{author_email}>", file=sys.stderr)

    # 9. Create branch
    branch_name = f"update-{item_type}/issue-{args.issue_number}-{slugify(item_name)}"

    if args.dry_run:
        print(f"\n=== DRY RUN RESULTS ===", file=sys.stderr)
        print(f"Item: {item_type} {item_id} ({item_name})", file=sys.stderr)
        print(f"Branch would be: {branch_name}", file=sys.stderr)
        print(f"Author: {author_name} <{author_email}>", file=sys.stderr)
        print(f"\nChanges:", file=sys.stderr)
        for line in build_change_summary(current, proposed):
            print(f"  {line}", file=sys.stderr)
        print(f"\nProposed JSON:", file=sys.stderr)
        print(json.dumps(proposed, indent=4), file=sys.stderr)
        return

    # Check for existing branch name
    existing = subprocess.run(
        ["git", "branch", "--list", branch_name],
        capture_output=True, text=True, cwd=project_root,
    )
    remote_existing = subprocess.run(
        ["git", "ls-remote", "--heads", "origin", branch_name],
        capture_output=True, text=True, cwd=project_root,
    )
    if existing.stdout.strip() or remote_existing.stdout.strip():
        for i in range(2, 100):
            candidate = f"{branch_name}-{i}"
            remote_check = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", candidate],
                capture_output=True, text=True, cwd=project_root,
            )
            local_check = subprocess.run(
                ["git", "branch", "--list", candidate],
                capture_output=True, text=True, cwd=project_root,
            )
            if not remote_check.stdout.strip() and not local_check.stdout.strip():
                branch_name = candidate
                break

    print(f"Creating branch: {branch_name}", file=sys.stderr)
    run(["git", "checkout", "-b", branch_name], cwd=project_root)

    try:
        # 10. Write updated file
        filepath = os.path.join(project_root, "data", TYPE_DIR[item_type], f"{item_id}.json")

        # Path traversal protection
        real_dir = os.path.realpath(os.path.join(project_root, "data", TYPE_DIR[item_type]))
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(real_dir + os.sep):
            print(f"Error: path traversal detected for {item_id}", file=sys.stderr)
            sys.exit(1)

        # Round-trip through Pydantic to ensure JSON uses alias keys (e.g. INAC-EX not INAC_EX)
        model_class = {"technique": Technique, "weakness": Weakness, "mitigation": Mitigation}[item_type]
        proposed = model_class.model_validate(proposed).model_dump(by_alias=True)

        with open(filepath, 'w') as f:
            json.dump(proposed, f, indent=4)
            f.write('\n')

        print(f"  Written: {filepath}", file=sys.stderr)

        # 11. Commit with original submitter as author
        run(["git", "add", filepath], cwd=project_root)

        type_label = item_type.capitalize()
        commit_msg = (
            f"Update {type_label}: {item_name} ({item_id})\n\n"
            f"Auto-implemented from issue #{args.issue_number}."
        )

        run([
            "git", "commit",
            "--author", f"{author_name} <{author_email}>",
            "-m", commit_msg,
        ], cwd=project_root)

        # 12. Push and create PR
        print("Pushing branch...", file=sys.stderr)
        run(["git", "push", "-u", "origin", branch_name], cwd=project_root)

        pr_title = f"Update {type_label}: {item_name} ({item_id})"

        # Build PR body
        change_summary = build_change_summary(current, proposed)

        pr_lines = []
        pr_lines.append(f"> **This PR was auto-generated** from an update {item_type} "
                        "submission. Please review the changes below before merging.")
        pr_lines.append("")
        pr_lines.append("## Summary")
        pr_lines.append("")
        pr_lines.append(f"Updates {item_type} from #{args.issue_number}.")
        pr_lines.append("")
        pr_lines.append("| Field | Value |")
        pr_lines.append("|---|---|")
        pr_lines.append(f"| Type | {type_label} |")
        pr_lines.append(f"| ID | `{item_id}` |")
        pr_lines.append(f"| Name | {item_name} |")
        pr_lines.append("")

        # Changes
        pr_lines.append("## Changes")
        pr_lines.append("")
        pr_lines.extend(change_summary)
        pr_lines.append("")

        # Before/After JSON
        pr_lines.append("<details><summary>Full JSON diff</summary>")
        pr_lines.append("")
        pr_lines.append("### Before")
        pr_lines.append("```json")
        pr_lines.append(json.dumps(current, indent=4))
        pr_lines.append("```")
        pr_lines.append("")
        pr_lines.append("### After")
        pr_lines.append("```json")
        pr_lines.append(json.dumps(proposed, indent=4))
        pr_lines.append("```")
        pr_lines.append("")
        pr_lines.append("</details>")
        pr_lines.append("")

        # Attribution
        pr_lines.append("## Attribution")
        pr_lines.append("")
        pr_lines.append(f"Original submission by @{issue['user']['login']} "
                        f"in #{args.issue_number}.")
        pr_lines.append(f"Commit authored as: {author_name} <{author_email}>")
        pr_lines.append("")
        pr_lines.append(f"Resolves #{args.issue_number}")

        pr_body = '\n'.join(pr_lines)

        # Write PR body to temp file to avoid command-line length limits
        pr_body_file = os.path.join(project_root, ".pr_body.md")
        with open(pr_body_file, 'w') as f:
            f.write(pr_body)

        try:
            pr_url = run([
                "gh", "pr", "create",
                "--head", branch_name,
                "--title", pr_title,
                "--body-file", pr_body_file,
            ], cwd=project_root)
        finally:
            if os.path.exists(pr_body_file):
                os.remove(pr_body_file)

        print(f"PR created: {pr_url}", file=sys.stderr)

        # 13. Post a comment on the original issue linking to the PR
        link_comment = f"PR created: {pr_url}"
        run(["gh", "issue", "comment", str(args.issue_number), "--body", link_comment])

        print(pr_url)

    except Exception as e:
        if not args.dry_run:
            print(f"Error during implementation: {e}", file=sys.stderr)
            subprocess.run(["git", "checkout", "-"], cwd=project_root,
                           capture_output=True, text=True)
        raise


if __name__ == "__main__":
    main()
