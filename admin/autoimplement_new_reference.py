#!/usr/bin/env python3
"""
Auto-implements a new reference by creating DFCite .txt and .bib files
and opening a PR.

Finds the preview comment with the REFERENCE_PREVIEW marker, extracts
the DFCite ID and file contents, writes them to data/references/, and
opens a PR attributed to the original issue submitter.

Usage:
    python3 admin/autoimplement_new_reference.py --issue-number 456
"""

import argparse
import json
import os
import re
import subprocess
import sys


# Strict ID pattern for DFCite references
VALID_DFCITE_RE = re.compile(r'^DFCite-\d{4,6}$')


def run(cmd, **kwargs):
    """Run a command and return its stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        result.check_returncode()
    return result.stdout.strip()


def validate_dfcite_id(dfcite_id):
    """Validate that a DFCite ID matches the expected format."""
    if not VALID_DFCITE_RE.match(dfcite_id):
        print(f"Error: invalid DFCite ID format: '{dfcite_id}'", file=sys.stderr)
        sys.exit(1)


def get_issue(issue_number):
    """Fetch issue metadata."""
    raw = run([
        "gh", "api",
        f"repos/{{owner}}/{{repo}}/issues/{issue_number}",
    ])
    return json.loads(raw)


def get_issue_comments(issue_number):
    """Fetch all comments on an issue."""
    raw = run([
        "gh", "api",
        f"repos/{{owner}}/{{repo}}/issues/{issue_number}/comments",
        "--paginate",
    ])
    return json.loads(raw)


def find_reference_preview(comments):
    """Find the preview comment with the REFERENCE_PREVIEW marker."""
    for comment in comments:
        body = comment.get("body", "")
        if "<!-- REFERENCE_PREVIEW -->" in body:
            return comment
    return None


def is_existing_match(comment_body):
    """Check if the preview comment indicates an existing reference match.

    Returns True if the reference already exists (no new file needed).
    """
    return "match an existing citation" in comment_body.lower()


def extract_dfcite_id(comment_body):
    """Extract the DFCite ID from the preview comment.

    Looks for: "A new reference can be assigned: **DFCite-XXXX**"
    """
    match = re.search(r'A new reference can be assigned: \*\*(\S+)\*\*', comment_body)
    if match:
        return match.group(1)
    return None


def extract_txt_content(comment_body):
    """Extract .txt file content from the preview comment.

    Looks for the code block after the .txt filename line.
    Format:
        **`data/references/DFCite-XXXX.txt`**
        ```
        citation text here
        ```
    """
    # Match the .txt filename followed by a code block
    pattern = re.compile(
        r'\*\*`data/references/DFCite-\d+\.txt`\*\*\s*\n'
        r'```\s*\n(.*?)\n```',
        re.DOTALL,
    )
    match = pattern.search(comment_body)
    if match:
        return match.group(1).strip()
    return None


def extract_bib_content(comment_body):
    """Extract .bib file content from the preview comment.

    Looks for a ```bibtex code block.
    """
    pattern = re.compile(r'```bibtex\s*\n(.*?)\n```', re.DOTALL)
    match = pattern.search(comment_body)
    if match:
        return match.group(1).strip()
    return None


def sanitise_git_value(value):
    """Remove characters that could cause issues in git --author strings."""
    return re.sub(r'[<>\n\r]', '', value).strip()


def get_submitter_info(issue):
    """Get the original submitter's name and noreply email for commit attribution."""
    user = issue["user"]
    login = user["login"]
    user_id = user["id"]

    raw = run(["gh", "api", f"users/{login}"])
    profile = json.loads(raw)
    name = sanitise_git_value(profile.get("name") or login)

    email = f"{user_id}+{login}@users.noreply.github.com"
    return name, email


def slugify(text, max_len=50):
    """Create a branch-safe slug from text."""
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return slug[:max_len].rstrip('-')


def main():
    parser = argparse.ArgumentParser(
        description="Auto-implement a new reference as a PR",
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

    project_root = args.project_root
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Fetch issue and comments
    print("Fetching issue...", file=sys.stderr)
    issue = get_issue(args.issue_number)
    comments = get_issue_comments(args.issue_number)

    # 2. Find the reference preview comment
    preview_comment = find_reference_preview(comments)
    if preview_comment is None:
        print("Error: could not find REFERENCE_PREVIEW comment. "
              "Has the issue been previewed?", file=sys.stderr)
        sys.exit(1)

    comment_body = preview_comment["body"]

    # 3. Check if this is an existing match (no action needed)
    if is_existing_match(comment_body):
        no_action_msg = (
            "This reference matches an existing citation — no new files are needed.\n\n"
            "The `autoimplement` label has been processed but no PR was created."
        )
        run(["gh", "issue", "comment", str(args.issue_number), "--body", no_action_msg])
        print("Reference matches existing citation — no action needed.", file=sys.stderr)
        print("NO_ACTION")
        sys.exit(0)

    # 4. Extract DFCite ID
    dfcite_id = extract_dfcite_id(comment_body)
    if dfcite_id is None:
        print("Error: could not extract DFCite ID from preview comment.",
              file=sys.stderr)
        sys.exit(1)

    validate_dfcite_id(dfcite_id)
    print(f"DFCite ID: {dfcite_id}", file=sys.stderr)

    # 5. Extract file contents
    txt_content = extract_txt_content(comment_body)
    if txt_content is None:
        print("Error: could not extract .txt content from preview comment.",
              file=sys.stderr)
        sys.exit(1)

    bib_content = extract_bib_content(comment_body)

    # 6. Race protection — check files don't already exist
    refs_dir = os.path.join(project_root, "data", "references")
    txt_path = os.path.join(refs_dir, f"{dfcite_id}.txt")
    bib_path = os.path.join(refs_dir, f"{dfcite_id}.bib")

    # Verify paths are inside the expected directory
    real_refs_dir = os.path.realpath(refs_dir)
    real_txt_path = os.path.realpath(txt_path)
    real_bib_path = os.path.realpath(bib_path)
    if not real_txt_path.startswith(real_refs_dir + os.sep):
        print(f"Error: path traversal detected for {dfcite_id}.txt", file=sys.stderr)
        sys.exit(1)
    if not real_bib_path.startswith(real_refs_dir + os.sep):
        print(f"Error: path traversal detected for {dfcite_id}.bib", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(txt_path):
        print(f"Error: {txt_path} already exists — {dfcite_id} may already be taken.",
              file=sys.stderr)
        sys.exit(1)
    if bib_content and os.path.exists(bib_path):
        print(f"Error: {bib_path} already exists — {dfcite_id} may already be taken.",
              file=sys.stderr)
        sys.exit(1)

    # 7. Get submitter info
    author_name, author_email = get_submitter_info(issue)
    print(f"Submitter: {author_name} <{author_email}>", file=sys.stderr)

    # 8. Create branch
    branch_name = f"new-reference/issue-{args.issue_number}-{slugify(dfcite_id)}"

    # Check if branch already exists
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
        # 9. Write files
        print("Writing reference files...", file=sys.stderr)
        written_files = []

        with open(txt_path, 'w') as f:
            f.write(txt_content + '\n')
        written_files.append(txt_path)
        print(f"  Written: {txt_path}", file=sys.stderr)

        if bib_content:
            with open(bib_path, 'w') as f:
                f.write(bib_content + '\n')
            written_files.append(bib_path)
            print(f"  Written: {bib_path}", file=sys.stderr)

        # 10. Commit
        for f in written_files:
            run(["git", "add", f], cwd=project_root)

        commit_msg = (
            f"Add new reference: {dfcite_id}\n\n"
            f"Auto-implemented from issue #{args.issue_number}."
        )

        run([
            "git", "commit",
            "--author", f"{author_name} <{author_email}>",
            "-m", commit_msg,
        ], cwd=project_root)

        # 11. Push and create PR
        print("Pushing branch...", file=sys.stderr)
        run(["git", "push", "-u", "origin", branch_name], cwd=project_root)

        pr_title = f"Add new reference: {dfcite_id}"

        # Build PR body
        pr_lines = []
        pr_lines.append("> **This PR was auto-generated** from a new reference "
                        "submission. Please review the files below before merging.")
        pr_lines.append("")
        pr_lines.append("## Summary")
        pr_lines.append("")
        pr_lines.append(f"Adds new reference `{dfcite_id}` from #{args.issue_number}.")
        pr_lines.append("")
        pr_lines.append("## Files")
        pr_lines.append("")
        for f in written_files:
            rel = os.path.relpath(f, project_root)
            pr_lines.append(f"- `{rel}`")
        pr_lines.append("")
        pr_lines.append("## Citation text")
        pr_lines.append("")
        pr_lines.append(f"> {txt_content}")
        pr_lines.append("")
        pr_lines.append("## Attribution")
        pr_lines.append("")
        pr_lines.append(f"Original submission by @{issue['user']['login']} "
                        f"in #{args.issue_number}.")
        pr_lines.append(f"Commit authored as: {author_name} <{author_email}>")
        pr_lines.append("")
        pr_lines.append(f"Resolves #{args.issue_number}")

        pr_body = '\n'.join(pr_lines)

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

        # 12. Comment on the original issue
        link_comment = f"PR created: {pr_url}"
        run(["gh", "issue", "comment", str(args.issue_number), "--body", link_comment])

        print(pr_url)

    except Exception as e:
        print(f"Error during implementation: {e}", file=sys.stderr)
        subprocess.run(["git", "checkout", "-"], cwd=project_root,
                       capture_output=True, text=True)
        raise


if __name__ == "__main__":
    main()
