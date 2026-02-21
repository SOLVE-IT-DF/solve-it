#!/usr/bin/env python3
"""
Assigns the next available technique ID to a proposed technique issue.

Finds the preview comment (containing "T____"), posts a confirmation of
the assigned ID, then posts the revised JSON with the real ID.
The original preview comment is left untouched.

Usage:
    python3 admin/assign_technique_id.py --issue-number 42
    python3 admin/assign_technique_id.py --issue-number 42 --project-root /path/to/solve-it
"""

import argparse
import json
import os
import subprocess
import sys

# Allow importing IDScanner from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_next_free_ids import IDScanner


def get_next_technique_id(project_root=None):
    """Find the next available technique ID.

    Scans both local files and GitHub issues/PRs so that IDs assigned
    to other issues (but not yet implemented into files) are not reused.
    The current issue still has "T____" at this point, so it won't
    match as a reserved ID.
    """
    scanner = IDScanner(project_root)
    scanner.scan_local_files()
    scanner.scan_github_issues_prs()
    next_ids = scanner.find_next_available(
        scanner.technique_ids, scanner.reserved_technique_ids, count=1,
    )
    return next_ids[0]


def get_issue_comments(issue_number):
    """Fetch all comments on an issue via the REST API.

    Uses the REST endpoint (not gh issue view) so that comment IDs are
    numeric, which is required for the PATCH endpoint.
    """
    result = subprocess.run(
        [
            "gh", "api",
            f"repos/{{owner}}/{{repo}}/issues/{issue_number}/comments",
            "--paginate",
        ],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def find_preview_comment(comments):
    """Return the preview comment dict that contains the T____ placeholder.

    The preview comment is posted by the technique-issue-preview workflow
    and contains a JSON block with "id": "T____".
    """
    for comment in comments:
        body = comment.get("body", "")
        if '"id": "T____"' in body:
            return comment
    return None


def post_comment(issue_number, body):
    """Post a new comment on an issue."""
    subprocess.run(
        ["gh", "issue", "comment", str(issue_number), "--body", body],
        capture_output=True, text=True, check=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Assign the next technique ID to a proposed technique issue",
    )
    parser.add_argument(
        "--issue-number", type=int, required=True,
        help="GitHub issue number",
    )
    parser.add_argument(
        "--project-root", type=str, default=None,
        help="Path to SOLVE-IT project root (default: auto-detect)",
    )
    args = parser.parse_args()

    # 1. Determine next available technique ID
    next_id = get_next_technique_id(args.project_root)
    technique_id = f"T{next_id}"
    print(f"Next available technique ID: {technique_id}", file=sys.stderr)

    # 2. Fetch issue comments and locate the preview comment
    comments = get_issue_comments(args.issue_number)
    preview = find_preview_comment(comments)

    if preview is None:
        print("Error: could not find a preview comment with T____ placeholder.",
              file=sys.stderr)
        sys.exit(1)

    old_body = preview["body"]

    # 3. Build revised JSON with real ID
    revised_body = old_body.replace("T____", technique_id)
    revised_body = revised_body.replace(
        "The technique ID (T____) will be assigned during review.",
        f"Technique ID **{technique_id}** has been assigned.",
    )

    if revised_body == old_body:
        print("Error: replacement produced no changes — is T____ already replaced?",
              file=sys.stderr)
        sys.exit(1)

    # 4. Post confirmation comment, then revised JSON
    confirmation = f"Assigned technique ID: **{technique_id}**"
    print(f"Posting confirmation and revised JSON for {technique_id}...",
          file=sys.stderr)
    post_comment(args.issue_number, confirmation)
    post_comment(args.issue_number, revised_body)

    # 6. Print assigned ID to stdout (for workflow to capture if needed)
    print(technique_id)


if __name__ == "__main__":
    main()
