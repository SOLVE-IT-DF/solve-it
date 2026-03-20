#!/usr/bin/env python3
"""
Auto-implements a technique move by updating solve-it.json and/or
technique subtechnique lists, and opening a PR.

Reads the issue body to determine which technique to move and where.
The destination prefix determines the move type:
  - DFO-xxxx → move/promote technique to an objective
  - DFT-xxxx → demote technique to be a subtechnique

Usage:
    python3 admin/autoimplement_move_technique.py --issue-number 300
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
    run, validate_id, sanitise_git_value, slugify, get_submitter_info,
    get_issue,
)
from parse_technique_issue import parse_issue_body
from parse_move_technique_issue import find_current_parent, find_current_objectives
from solve_it_library import KnowledgeBase


VALID_DFT_RE = re.compile(r'^DFT-\d{4,6}$')
VALID_DFO_RE = re.compile(r'^DFO-\d{4,6}$')
VALID_DEST_RE = re.compile(r'^(DFT|DFO)-\d{4,6}$')


def load_solve_it_json(project_root):
    """Load solve-it.json and return (data, filepath)."""
    filepath = os.path.join(project_root, "data", "solve-it.json")
    with open(filepath) as f:
        return json.load(f), filepath


def save_solve_it_json(filepath, data):
    """Write solve-it.json."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        f.write('\n')


def load_technique_json(project_root, technique_id):
    """Load a technique JSON file and return (data, filepath)."""
    filepath = os.path.join(project_root, "data", "techniques", f"{technique_id}.json")
    # Path traversal protection
    real_dir = os.path.realpath(os.path.join(project_root, "data", "techniques"))
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_dir + os.sep):
        print(f"Error: path traversal detected for {technique_id}", file=sys.stderr)
        sys.exit(1)
    with open(filepath) as f:
        return json.load(f), filepath


def save_technique_json(filepath, data):
    """Write a technique JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(
        description="Auto-implement a technique move as a PR",
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

    # 1. Fetch issue
    print("Fetching issue...", file=sys.stderr)
    issue = get_issue(args.issue_number)

    # 2. Parse issue body
    fields = parse_issue_body(issue["body"])
    technique_id = fields.get("Technique to move", "").strip()
    dest_id = fields.get("Destination", "").strip()

    if not VALID_DFT_RE.match(technique_id):
        print(f"Error: Invalid technique ID format: '{technique_id}'", file=sys.stderr)
        sys.exit(1)
    if not VALID_DEST_RE.match(dest_id):
        print(f"Error: Invalid destination ID format: '{dest_id}'", file=sys.stderr)
        sys.exit(1)
    if technique_id == dest_id:
        print("Error: technique cannot be moved to itself.", file=sys.stderr)
        sys.exit(1)

    validate_id(technique_id)

    # 3. Load KB and validate
    kb = KnowledgeBase(project_root, 'solve-it.json')

    technique = kb.get_technique(technique_id)
    if technique is None:
        print(f"Error: technique {technique_id} not found.", file=sys.stderr)
        sys.exit(1)

    technique_name = technique.get('name', technique_id)
    current_parent = find_current_parent(kb, technique_id)
    current_objectives = find_current_objectives(kb, technique_id)

    dest_is_objective = dest_id.startswith('DFO-')

    if dest_is_objective:
        # Validate objective exists
        dest_obj = None
        for obj in kb.list_objectives():
            if obj.get('id') == dest_id:
                dest_obj = obj
                break
        if dest_obj is None:
            print(f"Error: objective {dest_id} not found.", file=sys.stderr)
            sys.exit(1)
        dest_name = dest_obj.get('name', dest_id)

        # Check already there
        for obj_id, obj_name in current_objectives:
            if obj_id == dest_id:
                print(f"No move needed: {technique_id} is already under {dest_id}.",
                      file=sys.stderr)
                sys.exit(0)
    else:
        # Validate destination technique exists
        dest_technique = kb.get_technique(dest_id)
        if dest_technique is None:
            print(f"Error: destination technique {dest_id} not found.", file=sys.stderr)
            sys.exit(1)
        dest_name = dest_technique.get('name', dest_id)

    # 4. Describe what we're going to do
    if dest_is_objective:
        if current_parent:
            move_type = "Promote subtechnique to top-level technique"
        elif current_objectives:
            move_type = "Move technique to a different objective"
        else:
            move_type = "Add technique to objective"
    else:
        if current_parent:
            move_type = "Move subtechnique to a different parent technique"
        else:
            move_type = "Demote technique to subtechnique"

    print(f"Move type: {move_type}", file=sys.stderr)
    print(f"  Technique: {technique_id} ({technique_name})", file=sys.stderr)
    print(f"  Destination: {dest_id} ({dest_name})", file=sys.stderr)

    if args.dry_run:
        print(f"\n=== DRY RUN: would proceed with the above move ===", file=sys.stderr)
        return

    # 5. Get submitter info
    author_name, author_email = get_submitter_info(issue)
    print(f"Submitter: {author_name} <{author_email}>", file=sys.stderr)

    # 6. Create branch
    branch_name = f"move-technique/issue-{args.issue_number}-{slugify(technique_name)}"

    # Check for existing branch
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
        changed_files = []

        # 7. Apply the move
        # 7a. Remove from old parent's subtechniques list (if was a subtechnique)
        if current_parent:
            parent_data, parent_path = load_technique_json(project_root, current_parent)
            parent_data["subtechniques"] = [
                s for s in parent_data.get("subtechniques", []) if s != technique_id
            ]
            save_technique_json(parent_path, parent_data)
            changed_files.append(parent_path)
            print(f"  Removed {technique_id} from {current_parent} subtechniques", file=sys.stderr)

        # 7b. Remove from old objective(s) in solve-it.json (if was top-level)
        objectives_data, solve_it_path = load_solve_it_json(project_root)
        solve_it_changed = False

        if current_objectives:
            for obj in objectives_data:
                if technique_id in obj.get("techniques", []):
                    obj["techniques"] = [t for t in obj["techniques"] if t != technique_id]
                    solve_it_changed = True
                    print(f"  Removed {technique_id} from objective {obj['id']} ({obj['name']})",
                          file=sys.stderr)

        # 7c. Add to destination
        if dest_is_objective:
            # Add to objective's techniques list
            for obj in objectives_data:
                if obj.get("id") == dest_id:
                    if technique_id not in obj.get("techniques", []):
                        obj["techniques"].append(technique_id)
                        solve_it_changed = True
                        print(f"  Added {technique_id} to objective {dest_id} ({dest_name})",
                              file=sys.stderr)
                    break
        else:
            # Add to destination technique's subtechniques list
            dest_data, dest_path = load_technique_json(project_root, dest_id)
            if technique_id not in dest_data.get("subtechniques", []):
                dest_data.setdefault("subtechniques", []).append(technique_id)
                save_technique_json(dest_path, dest_data)
                changed_files.append(dest_path)
                print(f"  Added {technique_id} to {dest_id} subtechniques", file=sys.stderr)

        # Save solve-it.json if changed
        if solve_it_changed:
            save_solve_it_json(solve_it_path, objectives_data)
            changed_files.append(solve_it_path)
            print(f"  Updated solve-it.json", file=sys.stderr)

        if not changed_files:
            print("No changes to commit.", file=sys.stderr)
            sys.exit(0)

        # 8. Commit
        for f in changed_files:
            run(["git", "add", f], cwd=project_root)

        commit_msg = (
            f"Move technique: {technique_name} ({technique_id}) to {dest_id}\n\n"
            f"{move_type}.\n"
            f"Auto-implemented from issue #{args.issue_number}."
        )

        run([
            "git", "commit",
            "--author", f"{author_name} <{author_email}>",
            "-m", commit_msg,
        ], cwd=project_root)

        # 9. Push and create PR
        print("Pushing branch...", file=sys.stderr)
        run(["git", "push", "-u", "origin", branch_name], cwd=project_root)

        pr_title = f"Move technique: {technique_name} ({technique_id})"

        pr_lines = []
        pr_lines.append("> **This PR was auto-generated** from a move technique "
                        "submission. Please review the changes below before merging.")
        pr_lines.append("")
        pr_lines.append("## Summary")
        pr_lines.append("")
        pr_lines.append(f"**Move type:** {move_type}")
        pr_lines.append("")
        pr_lines.append("| Field | Value |")
        pr_lines.append("|---|---|")
        pr_lines.append(f"| Technique | `{technique_id}` ({technique_name}) |")
        pr_lines.append(f"| Destination | `{dest_id}` ({dest_name}) |")
        pr_lines.append(f"| Move type | {move_type} |")
        if current_parent:
            parent_technique = kb.get_technique(current_parent)
            parent_name = parent_technique.get('name', '') if parent_technique else ''
            pr_lines.append(f"| Previous parent | `{current_parent}` ({parent_name}) |")
        if current_objectives:
            obj_labels = ', '.join(f"`{oid}` ({oname})" for oid, oname in current_objectives)
            pr_lines.append(f"| Previous objective(s) | {obj_labels} |")
        pr_lines.append("")

        # Changes
        pr_lines.append("## Changes")
        pr_lines.append("")
        for f in changed_files:
            pr_lines.append(f"- `{os.path.relpath(f, project_root)}`")
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
                "--label", "content: move technique",
                "--label", "autoimplement",
            ], cwd=project_root)
        finally:
            if os.path.exists(pr_body_file):
                os.remove(pr_body_file)

        print(f"PR created: {pr_url}", file=sys.stderr)

        # Post a comment on the original issue linking to the PR
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
