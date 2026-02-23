#!/usr/bin/env python3
"""
Assigns the next available mitigation ID to a proposed mitigation issue.

Finds the preview comment (containing "M____"), posts a confirmation of
the assigned ID, then posts the revised JSON with the real ID.
The original preview comment is left untouched.

Usage:
    python3 admin/assign_mitigation_id.py --issue-number 42
    python3 admin/assign_mitigation_id.py --issue-number 42 --project-root /path/to/solve-it
"""

import argparse
import json
import os
import subprocess
import sys

# Allow importing IDScanner from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_next_free_ids import IDScanner


def get_next_mitigation_id(project_root=None):
    """Find the next available mitigation ID."""
    scanner = IDScanner(project_root)
    scanner.scan_local_files()
    scanner.scan_github_issues_prs()
    next_ids = scanner.find_next_available(
        scanner.mitigation_ids, scanner.reserved_mitigation_ids, count=1,
    )
    return next_ids[0]


def get_issue_comments(issue_number):
    """Fetch all comments on an issue via the REST API."""
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
    """Return the preview comment dict that contains the M____ placeholder."""
    for comment in comments:
        body = comment.get("body", "")
        if '"id": "M____"' in body:
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
        description="Assign the next mitigation ID to a proposed mitigation issue",
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

    # 1. Determine next available mitigation ID
    next_id = get_next_mitigation_id(args.project_root)
    mitigation_id = f"M{next_id}"
    print(f"Next available mitigation ID: {mitigation_id}", file=sys.stderr)

    # 2. Fetch issue comments and locate the preview comment
    comments = get_issue_comments(args.issue_number)
    preview = find_preview_comment(comments)

    if preview is None:
        print("Error: could not find a preview comment with M____ placeholder.",
              file=sys.stderr)
        sys.exit(1)

    old_body = preview["body"]

    # 3. Build revised JSON with real ID
    revised_body = old_body.replace("M____", mitigation_id)
    revised_body = revised_body.replace(
        "Thanks for proposing a new mitigation! Here's what it would look like as JSON:",
        "Your mitigation has been assigned an ID. Here is an updated copy of the JSON data with the ID completed:",
    )
    revised_body = revised_body.replace(
        "The mitigation ID (M____) will be assigned during review.",
        f"Mitigation ID **{mitigation_id}** has been assigned.",
    )

    if revised_body == old_body:
        print("Error: replacement produced no changes — is M____ already replaced?",
              file=sys.stderr)
        sys.exit(1)

    # 4. Post confirmation comment, then revised JSON
    confirmation = f"Assigned mitigation ID: **{mitigation_id}**"
    print(f"Posting confirmation and revised JSON for {mitigation_id}...",
          file=sys.stderr)
    post_comment(args.issue_number, confirmation)
    post_comment(args.issue_number, revised_body)

    # 5. Print assigned ID to stdout
    print(mitigation_id)


if __name__ == "__main__":
    main()
