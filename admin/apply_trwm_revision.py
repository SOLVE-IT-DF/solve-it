#!/usr/bin/env python3
"""
Applies a revision comment to a TRWM submission issue.

A submitter (or a maintainer) revises a TRWM submission by posting a comment
headed "### TRWM revision" with the revised TRWM Helper export in a fenced
JSON block. This script:

1. Checks the commenter may revise the submission and that IDs have not yet
   been assigned
2. Extracts and checks the revised JSON
3. Rebuilds the preview from it, using the issue body's form fields
4. Rewrites the first preview comment in place, so every later step (ID
   assignment, implementation) reads the revised version
5. Replies with a summary of what changed since the previous revision,
   or with the reason the revision was not applied
6. Adds labels for any new content types (never removes labels)

Usage (normally from .github/workflows/trwm-revision.yml):
    python3 admin/apply_trwm_revision.py --issue-number 713 \\
        --comment-id 123456 --comment-body-file comment_body.md \\
        --commenter octocat --association NONE --project-root .
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'issue_parsers'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_trwm_submission import (  # noqa: E402
    SubmissionError, generate_preview, load_trwm_json,
    preview_hash, stored_preview_hash,
)
from trwm_revision_diff import diff_previews, render_summary  # noqa: E402


REVISION_HEADING = "### TRWM revision"
PREVIEW_MARKER = "<!-- TRWM_PREVIEW -->"
ASSIGNED_LABEL = "assigned ID"
# GitHub's author_association values for people with standing in the repo.
# In an organisation repo, owners and org members show as OWNER or MEMBER,
# not COLLABORATOR, so all three are accepted.
TRUSTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

SOURCE_RE = re.compile(r'<!-- TRWM_SOURCE: comment (\d+) revision (\d+) -->')
FENCE_RE = re.compile(r'^```[ \t]*(json)?[ \t]*\n(.*?)\n```[ \t]*$', re.DOTALL | re.MULTILINE)


# ── Pure rules (unit-tested) ──────────────────────────────────────────

def can_revise(commenter, issue_author, association):
    """The issue author, or anyone the repo trusts, may post a revision."""
    if commenter and issue_author and commenter.lower() == issue_author.lower():
        return True
    return (association or "").upper() in TRUSTED_ASSOCIATIONS


def ids_assigned(labels):
    return ASSIGNED_LABEL in labels


def extract_revision_json(comment_body):
    """Return the parsed export from a revision comment.

    The JSON is the first fenced block after the "### TRWM revision"
    heading. Raises SubmissionError, with a message for the commenter,
    when there is no heading, no block, or the block is not a valid export.
    """
    body = comment_body.replace('\r\n', '\n')
    heading = re.search(r'^###[ \t]+TRWM revision[ \t]*$', body, re.MULTILINE | re.IGNORECASE)
    if not heading:
        raise SubmissionError(f'No "{REVISION_HEADING}" heading found in the comment.')
    fence = FENCE_RE.search(body, heading.end())
    if not fence:
        raise SubmissionError(
            f'No fenced JSON block found after the "{REVISION_HEADING}" heading. '
            'Paste the revision exactly as the TRWM Helper copied it.')
    return load_trwm_json(fence.group(2), source="revision JSON")


def find_preview_comment(comments):
    """The first preview comment: the one ID assignment and implementation read."""
    for comment in comments:
        if PREVIEW_MARKER in (comment.get("body") or ""):
            return comment
    return None


def current_revision_number(preview_body):
    """Revision number of a preview: 1 if built from the issue body."""
    match = SOURCE_RE.search(preview_body)
    return int(match.group(2)) if match else 1


def preview_was_hand_edited(preview_body):
    """True if the preview no longer matches the hash written with it.

    A preview with no hash marker (written before markers existed) cannot
    be checked, and is treated as unedited.
    """
    stored = stored_preview_hash(preview_body)
    return stored is not None and stored != preview_hash(preview_body)


def labels_to_add(wanted, current):
    """Labels from the new preview that the issue does not have yet."""
    return [label for label in wanted if label not in current]


def build_success_reply(revision, previous, summary, preview_url, hand_edited):
    lines = [f"**Revision {revision} applied** to the [preview]({preview_url}).", ""]
    if hand_edited:
        lines.append(":warning: The preview had been edited by hand since it was last "
                     "generated, and this revision replaced those edits. To see what they "
                     "were, open the \"edited\" history on the preview. If they're still "
                     "needed, the submitter should make the same changes in the Helper and "
                     "send another revision.")
        lines.append("")
    lines.append(f"Changes since revision {previous}:")
    lines.append("")
    lines.append(summary)
    lines.append("")
    lines.append("For further changes, send another revision the same way: in the "
                 "TRWM Helper app, **Import from GitHub** loads this latest version.")
    return "\n".join(lines) + "\n"


def build_failure_reply(reason):
    return ("**This revision was not applied.** The preview is unchanged.\n\n"
            f"{reason}\n")


# ── GitHub calls ──────────────────────────────────────────────────────

def gh_json(path):
    result = subprocess.run(["gh", "api", path],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def gh_list(path):
    """All pages of a list endpoint as one list. --slurp wraps the pages in
    an outer array; without it, --paginate prints one array per page."""
    result = subprocess.run(["gh", "api", path, "--paginate", "--slurp"],
                            capture_output=True, text=True, check=True)
    return [item for page in json.loads(result.stdout) for item in page]


def update_comment(comment_id, body):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({"body": body}, f)
        payload = f.name
    try:
        subprocess.run(["gh", "api", "-X", "PATCH",
                        f"repos/{{owner}}/{{repo}}/issues/comments/{int(comment_id)}",
                        "--input", payload],
                       capture_output=True, text=True, check=True)
    finally:
        os.unlink(payload)


def post_comment(issue_number, body):
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(body)
        path = f.name
    try:
        subprocess.run(["gh", "issue", "comment", str(int(issue_number)), "--body-file", path],
                       text=True, check=True)
    finally:
        os.unlink(path)


def add_labels(issue_number, labels):
    for label in labels:
        result = subprocess.run(["gh", "issue", "edit", str(int(issue_number)),
                                 "--add-label", label],
                                capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: could not add label '{label}': {result.stderr.strip()}",
                  file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Apply a TRWM revision comment")
    parser.add_argument('--issue-number', type=int, required=True)
    parser.add_argument('--comment-id', type=int, required=True)
    parser.add_argument('--comment-body-file', required=True)
    parser.add_argument('--commenter', required=True)
    parser.add_argument('--association', default="NONE",
                        help="The comment's author_association from the event")
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--dry-run', action='store_true',
                        help="Print what would be posted instead of calling GitHub")
    args = parser.parse_args()

    with open(args.comment_body_file) as f:
        comment_body = f.read()

    issue = gh_json(f"repos/{{owner}}/{{repo}}/issues/{args.issue_number}")
    labels = [label["name"] for label in issue.get("labels", [])]
    issue_author = (issue.get("user") or {}).get("login", "")

    def refuse(reason):
        reply = build_failure_reply(reason)
        if args.dry_run:
            print(reply)
        else:
            post_comment(args.issue_number, reply)
        print(f"Revision not applied: {reason}", file=sys.stderr)

    if not can_revise(args.commenter, issue_author, args.association):
        refuse("Only the person who opened this issue, or a maintainer of the "
               "repository, can revise a TRWM submission. If you have changes to "
               "suggest, describe them in a comment instead.")
        return

    if ids_assigned(labels):
        refuse(f"IDs have already been assigned (the `{ASSIGNED_LABEL}` label is on), "
               "so the submission can no longer be revised this way. Ask a maintainer "
               f"to remove the `{ASSIGNED_LABEL}` label first if the revision is still needed.")
        return

    comments = gh_list(f"repos/{{owner}}/{{repo}}/issues/{args.issue_number}/comments")
    preview = find_preview_comment(comments)
    if preview is None:
        refuse("No preview comment was found on this issue, so there is nothing to revise. "
               "A maintainer can regenerate the preview by closing and reopening the issue.")
        return

    try:
        trwm_data = extract_revision_json(comment_body)
    except SubmissionError as e:
        refuse(str(e))
        return

    this_comment = next((c for c in comments if c.get("id") == args.comment_id), {})
    previous = current_revision_number(preview["body"])
    revision = previous + 1
    revision_info = {
        "comment_id": args.comment_id,
        "revision": revision,
        "user": args.commenter,
        "date": ((this_comment.get("created_at") or "")[:10]
                 or datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    }

    try:
        new_preview, wanted_labels = generate_preview(
            issue.get("body") or "", args.project_root,
            trwm_data=trwm_data, revision_info=revision_info)
    except SubmissionError as e:
        refuse(str(e))
        return

    hand_edited = preview_was_hand_edited(preview["body"])
    summary = render_summary(diff_previews(preview["body"], new_preview))
    reply = build_success_reply(revision, previous, summary,
                                preview.get("html_url", ""), hand_edited)
    new_labels = labels_to_add(wanted_labels, labels)

    if args.dry_run:
        print(new_preview)
        print("\n----- reply -----\n")
        print(reply)
        print(f"Labels to add: {new_labels}")
        return

    update_comment(preview["id"], new_preview)
    post_comment(args.issue_number, reply)
    add_labels(args.issue_number, new_labels)
    print(f"Applied revision {revision} to issue #{args.issue_number}", file=sys.stderr)


if __name__ == '__main__':
    main()
