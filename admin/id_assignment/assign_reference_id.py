#!/usr/bin/env python3
"""
Assigns the next available DFCite ID to a proposed reference issue.

Finds the preview comment (containing "DFCite-____"), assigns a real DFCite ID,
and posts a revised comment with the real ID replacing the placeholder.

Usage:
    python3 admin/id_assignment/assign_reference_id.py --issue-number 456
"""

import argparse
import json
import re
import subprocess
import sys
import os

# Allow importing IDScanner from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_next_free_ids import IDScanner


def get_next_dfcite_id(project_root=None):
    """Find the next available DFCite ID.

    Scans both local files and GitHub issues/PRs so that IDs assigned
    to other issues (but not yet implemented into files) are not reused.
    """
    scanner = IDScanner(project_root)
    scanner.scan_local_files()
    scanner.scan_github_issues_prs()
    next_ids = scanner.find_next_available(
        scanner.citation_ids, scanner.reserved_citation_ids, count=1,
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
    """Return the preview comment that contains a DFCite-____ placeholder."""
    for comment in comments:
        body = comment.get("body", "")
        if "<!-- REFERENCE_PREVIEW -->" in body and "DFCite-____" in body:
            return comment
    return None


def post_comment(issue_number, body):
    """Post a new comment on an issue."""
    subprocess.run(
        ["gh", "issue", "comment", str(issue_number), "--body", body],
        text=True, check=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Assign the next DFCite ID to a proposed reference issue",
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

    # 1. Determine next available DFCite ID
    next_num = get_next_dfcite_id(args.project_root)
    dfcite_id = f"DFCite-{next_num}"
    print(f"Next available DFCite ID: {dfcite_id}", file=sys.stderr)

    # 2. Fetch issue comments and locate the preview comment
    comments = get_issue_comments(args.issue_number)
    preview = find_preview_comment(comments)

    if preview is None:
        print("Error: could not find a preview comment with DFCite-____ placeholder.",
              file=sys.stderr)
        sys.exit(1)

    old_body = preview["body"]

    # 3. Build revised body with real ID
    revised_body = old_body.replace("DFCite-____", dfcite_id)
    revised_body = revised_body.replace(
        "No existing match found. A reference ID will be assigned during review.",
        f"Reference ID **{dfcite_id}** has been assigned.",
    )

    if revised_body == old_body:
        print("Error: replacement produced no changes — is DFCite-____ already replaced?",
              file=sys.stderr)
        sys.exit(1)

    # 4. Post confirmation comment, then revised preview
    confirmation = f"Assigned reference ID: **{dfcite_id}**"
    print(f"Posting confirmation and revised preview for {dfcite_id}...",
          file=sys.stderr)
    post_comment(args.issue_number, confirmation)
    post_comment(args.issue_number, revised_body)

    # 5. Print assigned ID to stdout
    print(dfcite_id)


if __name__ == "__main__":
    main()
