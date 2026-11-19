#!/usr/bin/env python3
"""
Converts an existing issue into a TRWM submission.

Older issues, such as placeholder "Create new technique" issues, were not
opened with the TRWM submission form, so the TRWM tooling ignored them. A
fuller version can now be added to such an issue without opening a new one:

1. The TRWM Helper export is posted as a comment headed "### TRWM revision"
   (what the Helper's Submit card copies once the session is linked to the
   issue) or "### TRWM submission", with the JSON in a fenced block.
2. A maintainer adds the `trwm-convert` label.

This script, run by .github/workflows/trwm-convert.yml, then:

- checks the issue is not already a TRWM submission and has no IDs assigned
- takes the newest such comment by the issue's author or a maintainer
- builds the TRWM preview from it, taking the submission type, objective
  and parent technique from the export since the issue has no TRWM form
- posts the preview, adds the `trwm` label and the content labels, and
  removes `trwm-convert`

From then on the issue is an ordinary TRWM submission: revisions, ID
assignment and implementation work as for one opened with the form.

Usage:
    python3 admin/convert_to_trwm.py --issue-number 271 --project-root .
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'issue_parsers'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parse_trwm_submission import SubmissionError, generate_preview, load_trwm_json  # noqa: E402
from apply_trwm_revision import (  # noqa: E402
    ASSIGNED_LABEL, FENCE_RE, add_labels, can_revise, find_preview_comment,
    gh_json, gh_list, post_comment,
)

CONVERT_LABEL = "trwm-convert"
TRWM_LABEL = "trwm"
HEADING_RE = re.compile(r'^###[ \t]+TRWM (?:revision|submission)[ \t]*$',
                        re.MULTILINE | re.IGNORECASE)
BOT_LOGIN = "github-actions[bot]"


# ── Pure rules (unit-tested) ──────────────────────────────────────────

def has_export_heading(body):
    return bool(HEADING_RE.search((body or "").replace('\r\n', '\n')))


def find_source_comment(comments, issue_author):
    """The newest comment holding a TRWM export from someone who may submit.

    That is the issue's author or anyone the repository trusts, the same
    people who may revise a TRWM submission. Comments from others are
    skipped rather than refused, so an export pasted by someone else cannot
    be converted by mistake.
    """
    for comment in reversed(comments):
        user = (comment.get("user") or {}).get("login", "")
        if user == BOT_LOGIN or not has_export_heading(comment.get("body")):
            continue
        if can_revise(user, issue_author, comment.get("author_association")):
            return comment
    return None


def extract_export(comment_body):
    """Parse the export from the first fenced block after the heading."""
    body = comment_body.replace('\r\n', '\n')
    heading = HEADING_RE.search(body)
    if not heading:
        raise SubmissionError('No "### TRWM revision" or "### TRWM submission" heading found.')
    fence = FENCE_RE.search(body, heading.end())
    if not fence:
        raise SubmissionError(
            "No fenced JSON block was found after the heading. Paste the export "
            "exactly as the TRWM Helper copied it.")
    return load_trwm_json(fence.group(2), source="TRWM export comment")


def refusal_reason(labels, has_preview):
    """Why the issue cannot be converted, or None if it can."""
    if TRWM_LABEL in labels or has_preview:
        return ("This issue is already a TRWM submission. To change it, post the "
                "new export as a `### TRWM revision` comment instead.")
    if ASSIGNED_LABEL in labels:
        return (f"This issue already has IDs assigned (the `{ASSIGNED_LABEL}` label "
                "is on), so it cannot be converted to a TRWM submission.")
    return None


def build_failure_reply(reason):
    return ("**This issue was not converted to a TRWM submission.**\n\n"
            f"{reason}\n\n"
            f"Once that is sorted, add the `{CONVERT_LABEL}` label again.\n")


NO_SOURCE_REASON = (
    "No comment holding a TRWM export was found from the issue's author or a "
    "maintainer. In the TRWM Helper, link the session to this issue on the "
    "Summary tab and copy the revision it offers, or paste the exported JSON "
    "in a comment under a line reading `### TRWM submission`, in a `json` "
    "code block.")


# ── GitHub calls ──────────────────────────────────────────────────────

def remove_label(issue_number, label):
    result = subprocess.run(["gh", "issue", "edit", str(int(issue_number)),
                             "--remove-label", label],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: could not remove label '{label}': {result.stderr.strip()}",
              file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Convert an issue into a TRWM submission")
    parser.add_argument('--issue-number', type=int, required=True)
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--dry-run', action='store_true',
                        help="Print what would be posted instead of calling GitHub")
    args = parser.parse_args()

    issue = gh_json(f"repos/{{owner}}/{{repo}}/issues/{args.issue_number}")
    labels = [label["name"] for label in issue.get("labels", [])]
    issue_author = (issue.get("user") or {}).get("login", "")
    comments = gh_list(f"repos/{{owner}}/{{repo}}/issues/{args.issue_number}/comments")

    def finish(reply, new_labels=()):
        if args.dry_run:
            print(reply)
            print(f"Labels to add: {list(new_labels)}; label to remove: {CONVERT_LABEL}")
            return
        post_comment(args.issue_number, reply)
        add_labels(args.issue_number, list(new_labels))
        # Removed whatever the outcome, so adding it again retries.
        remove_label(args.issue_number, CONVERT_LABEL)

    reason = refusal_reason(labels, find_preview_comment(comments) is not None)
    if reason:
        finish(build_failure_reply(reason))
        print(f"Not converted: {reason}", file=sys.stderr)
        return

    source = find_source_comment(comments, issue_author)
    if source is None:
        finish(build_failure_reply(NO_SOURCE_REASON))
        print("Not converted: no export comment", file=sys.stderr)
        return

    revision_info = {
        "comment_id": source["id"],
        "revision": 1,
        "user": (source.get("user") or {}).get("login", "unknown"),
        "date": ((source.get("created_at") or "")[:10]
                 or datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "converted": True,
    }
    try:
        trwm_data = extract_export(source.get("body") or "")
        preview, wanted = generate_preview(
            issue.get("body") or "", args.project_root,
            trwm_data=trwm_data, revision_info=revision_info)
    except SubmissionError as e:
        finish(build_failure_reply(f"The export could not be read: {e}"))
        print(f"Not converted: {e}", file=sys.stderr)
        return

    new_labels = [TRWM_LABEL] + [label for label in wanted
                                 if label not in labels and label != TRWM_LABEL]
    finish(preview, new_labels)
    print(f"Converted issue #{args.issue_number} from comment {source['id']}", file=sys.stderr)


if __name__ == '__main__':
    main()
