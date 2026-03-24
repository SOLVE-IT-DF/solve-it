#!/usr/bin/env python3
"""
Auto-implements a reference update by modifying DFCite .txt and .bib files
and opening a PR.

Finds the preview comment with the REFERENCE_UPDATE_PREVIEW marker, extracts
the proposed changes from the JSON data block, applies them, and opens a PR
attributed to the original issue submitter.

Usage:
    python3 admin/autoimplement_update_reference.py --issue-number 399
"""

import argparse
import json
import os
import re
import subprocess
import sys


# Strict ID patterns
VALID_DFCITE_RE = re.compile(r'^DFCite-\d{4,6}$')
VALID_ITEM_ID_RE = re.compile(r'^(DFT|DFW|DFM)-\d{4,6}$')


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


def find_update_preview(comments):
    """Find the preview comment with the REFERENCE_UPDATE_PREVIEW marker."""
    for comment in reversed(comments):
        body = comment.get("body", "")
        if "<!-- REFERENCE_UPDATE_PREVIEW -->" in body:
            return comment
    return None


def extract_data_block(comment_body):
    """Extract the JSON data block from the preview comment.

    Looks for the ```json code block in the Data section.
    """
    pattern = re.compile(r'### Data\s*\n+```json\s*\n(.*?)\n```', re.DOTALL)
    match = pattern.search(comment_body)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def resolve_item_path(item_id, project_root):
    """Map an item ID to its JSON file path.

    Returns the path if the file exists, None otherwise.
    Validates against path traversal.
    """
    if not VALID_ITEM_ID_RE.match(item_id):
        return None

    prefix_to_dir = {
        "DFT": "techniques",
        "DFW": "weaknesses",
        "DFM": "mitigations",
    }
    prefix = item_id.split("-")[0]
    subdir = prefix_to_dir.get(prefix)
    if subdir is None:
        return None

    data_dir = os.path.join(project_root, "data", subdir)
    filepath = os.path.join(data_dir, f"{item_id}.json")

    # Path traversal check
    real_dir = os.path.realpath(data_dir)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_dir + os.sep):
        return None

    if not os.path.exists(filepath):
        return None

    return filepath


def add_reference_to_item(filepath, dfcite_id, relevance_summary):
    """Add a DFCite reference to an item's references array.

    Returns "added", "exists", or "error".
    """
    try:
        with open(filepath) as f:
            item_data = json.load(f)

        references = item_data.get("references", [])

        # Check if already present
        for ref in references:
            if isinstance(ref, dict) and ref.get("DFCite_id") == dfcite_id:
                return "exists"

        references.append({
            "DFCite_id": dfcite_id,
            "relevance_summary_280": relevance_summary,
        })
        item_data["references"] = references

        with open(filepath, 'w') as f:
            json.dump(item_data, f, indent=4)
            f.write('\n')

        return "added"
    except Exception:
        return "error"


def update_reference_relevance(filepath, dfcite_id, relevance_summary):
    """Update the relevance_summary_280 for an existing DFCite reference in an item.

    Returns "updated", "not found", or "error".
    """
    try:
        with open(filepath) as f:
            item_data = json.load(f)

        for ref in item_data.get("references", []):
            if isinstance(ref, dict) and ref.get("DFCite_id") == dfcite_id:
                ref["relevance_summary_280"] = relevance_summary
                with open(filepath, 'w') as f:
                    json.dump(item_data, f, indent=4)
                    f.write('\n')
                return "updated"

        return "not found"
    except Exception:
        return "error"


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
        description="Auto-implement a reference update as a PR",
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

    # 2. Find the reference update preview comment
    preview_comment = find_update_preview(comments)
    if preview_comment is None:
        print("Error: could not find REFERENCE_UPDATE_PREVIEW comment. "
              "Has the issue been previewed?", file=sys.stderr)
        sys.exit(1)

    comment_body = preview_comment["body"]

    # 3. Extract data block
    data = extract_data_block(comment_body)
    if data is None:
        print("Error: could not extract JSON data block from preview comment.",
              file=sys.stderr)
        sys.exit(1)

    dfcite_id = data.get("dfcite_id", "")
    validate_dfcite_id(dfcite_id)
    print(f"DFCite ID: {dfcite_id}", file=sys.stderr)

    new_txt = data.get("new_txt")
    new_bib = data.get("new_bib")
    cite_items = data.get("cite_in_items", [])
    update_relevance_items = data.get("update_relevance_items", [])

    if not new_txt and not new_bib and not cite_items and not update_relevance_items:
        no_action_msg = (
            "No changes detected in the preview data — nothing to implement.\n\n"
            "The `autoimplement` label has been processed but no PR was created."
        )
        run(["gh", "issue", "comment", str(args.issue_number), "--body", no_action_msg])
        print("No changes to implement.", file=sys.stderr)
        print("NO_ACTION")
        sys.exit(0)

    # 4. Validate reference files exist
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

    # For file updates, the .txt file should already exist
    if (new_txt or new_bib) and not os.path.exists(txt_path) and not os.path.exists(bib_path):
        print(f"Error: neither {dfcite_id}.txt nor {dfcite_id}.bib exist — "
              "cannot update a reference that doesn't exist.", file=sys.stderr)
        sys.exit(1)

    # 5. Get submitter info
    author_name, author_email = get_submitter_info(issue)
    print(f"Submitter: {author_name} <{author_email}>", file=sys.stderr)

    # 6. Create branch
    branch_name = f"update-reference/issue-{args.issue_number}-{slugify(dfcite_id)}"

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
        # 7. Apply changes
        written_files = []
        changes_summary = []

        # Update .txt file
        if new_txt:
            print(f"Updating {dfcite_id}.txt...", file=sys.stderr)
            with open(txt_path, 'w') as f:
                f.write(new_txt + '\n')
            written_files.append(txt_path)
            changes_summary.append("citation text")

        # Update .bib file
        if new_bib:
            print(f"Updating {dfcite_id}.bib...", file=sys.stderr)
            with open(bib_path, 'w') as f:
                f.write(new_bib + '\n')
            written_files.append(bib_path)
            changes_summary.append("BibTeX")

        # Add cite-in-items
        cite_results = []
        if cite_items:
            print("Adding reference to cited items...", file=sys.stderr)
            for item in cite_items:
                item_id = item.get("item_id", "")
                relevance = item.get("relevance_summary", "")
                item_path = resolve_item_path(item_id, project_root)
                if item_path is None:
                    cite_results.append((item_id, "not found"))
                    print(f"  Skipped: {item_id} (not found)", file=sys.stderr)
                    continue
                status = add_reference_to_item(item_path, dfcite_id, relevance)
                cite_results.append((item_id, status))
                if status == "added":
                    written_files.append(item_path)
                print(f"  {item_id}: {status}", file=sys.stderr)

        # Update relevance for items that already cite this reference
        relevance_results = []
        if update_relevance_items:
            print("Updating relevance summaries...", file=sys.stderr)
            for item in update_relevance_items:
                item_id = item.get("item_id", "")
                relevance = item.get("relevance_summary", "")
                item_path = resolve_item_path(item_id, project_root)
                if item_path is None:
                    relevance_results.append((item_id, "not found"))
                    print(f"  Skipped: {item_id} (not found)", file=sys.stderr)
                    continue
                status = update_reference_relevance(
                    item_path, dfcite_id, relevance,
                )
                relevance_results.append((item_id, status))
                if status == "updated":
                    written_files.append(item_path)
                print(f"  {item_id}: {status}", file=sys.stderr)

        if not written_files:
            no_action_msg = (
                "No files were changed (items may already cite this reference).\n\n"
                "The `autoimplement` label has been processed but no PR was created."
            )
            run(["gh", "issue", "comment", str(args.issue_number),
                 "--body", no_action_msg])
            run(["git", "checkout", "-"], cwd=project_root)
            print("No files changed — no PR needed.", file=sys.stderr)
            print("NO_ACTION")
            sys.exit(0)

        # 8. Commit
        for f in written_files:
            run(["git", "add", f], cwd=project_root)

        items_added = sum(1 for _, s in cite_results if s == "added")
        items_updated = sum(1 for _, s in relevance_results if s == "updated")
        extra_parts = []
        if items_added:
            extra_parts.append(f"cite in {items_added} item(s)")
        if items_updated:
            extra_parts.append(f"update relevance in {items_updated} item(s)")
        extra_suffix = ""
        if extra_parts:
            extra_suffix = " and " + ", ".join(extra_parts)

        file_changes = " and ".join(changes_summary)
        if file_changes:
            commit_msg = (
                f"Update reference {dfcite_id}: {file_changes}{extra_suffix}\n\n"
                f"Auto-implemented from issue #{args.issue_number}."
            )
        else:
            commit_msg = (
                f"Update reference {dfcite_id}: {', '.join(extra_parts)}\n\n"
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

        pr_title = f"Update reference: {dfcite_id}"

        # Build PR body
        pr_lines = []
        pr_lines.append("> **This PR was auto-generated** from a reference update "
                        "submission. Please review the changes below before merging.")
        pr_lines.append("")
        pr_lines.append("## Summary")
        pr_lines.append("")
        pr_lines.append(f"Updates reference `{dfcite_id}` from #{args.issue_number}.")
        pr_lines.append("")

        if changes_summary:
            pr_lines.append("## Changes")
            pr_lines.append("")
            for change in changes_summary:
                pr_lines.append(f"- Updated {change}")
            pr_lines.append("")

        pr_lines.append("## Files")
        pr_lines.append("")
        for f in written_files:
            rel = os.path.relpath(f, project_root)
            pr_lines.append(f"- `{rel}`")
        pr_lines.append("")

        if new_txt:
            pr_lines.append("## Updated citation text")
            pr_lines.append("")
            pr_lines.append(f"> {new_txt}")
            pr_lines.append("")

        if cite_results:
            pr_lines.append("## Cited in items")
            pr_lines.append("")
            pr_lines.append("| Item | Status |")
            pr_lines.append("|---|---|")
            for item_id, status in cite_results:
                pr_lines.append(f"| `{item_id}` | {status} |")
            pr_lines.append("")

        if relevance_results:
            pr_lines.append("## Relevance updates")
            pr_lines.append("")
            pr_lines.append("| Item | Status |")
            pr_lines.append("|---|---|")
            for item_id, status in relevance_results:
                pr_lines.append(f"| `{item_id}` | {status} |")
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
                "--label", "content: update reference",
                "--label", "autoimplement",
            ], cwd=project_root)
        finally:
            if os.path.exists(pr_body_file):
                os.remove(pr_body_file)

        print(f"PR created: {pr_url}", file=sys.stderr)

        # 10. Comment on the original issue
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
