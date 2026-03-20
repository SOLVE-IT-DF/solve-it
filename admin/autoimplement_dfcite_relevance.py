#!/usr/bin/env python3
"""
Auto-implements a DFCite relevance summary update by modifying the data file
and opening a PR.

Finds the preview comment with the DFCITE_RELEVANCE_UPDATE marker, extracts
the JSON block, updates the relevant data file, and opens a PR attributed to
the original issue submitter.

Usage:
    python3 admin/autoimplement_dfcite_relevance.py --issue-number 456
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library.reference_matching import load_reference_corpus


# Strict ID patterns — only allow expected format to prevent path traversal
VALID_ITEM_ID_RE = re.compile(r'^(DFT|DFW|DFM)-\d{4,6}$')
VALID_DFCITE_RE = re.compile(r'^DFCite-\d{4,6}$')


def run(cmd, **kwargs):
    """Run a command and return its stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        result.check_returncode()
    return result.stdout.strip()


def validate_item_id(item_id):
    """Validate that an item ID matches the expected format."""
    if not VALID_ITEM_ID_RE.match(item_id):
        print(f"Error: invalid item ID format: '{item_id}'", file=sys.stderr)
        sys.exit(1)


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


def find_relevance_comment(comments):
    """Find the preview comment with the DFCITE_RELEVANCE_UPDATE marker."""
    for comment in comments:
        body = comment.get("body", "")
        if "<!-- DFCITE_RELEVANCE_UPDATE -->" in body:
            return comment
    return None


def extract_json_block(comment_body):
    """Extract the JSON code block from the comment body.

    Returns the parsed dict with item_type, item_id, dfcite_id, relevance_summary_280.
    """
    pattern = re.compile(r'```json\s*\n(.*?)\n```', re.DOTALL)
    for match in pattern.finditer(comment_body):
        try:
            data = json.loads(match.group(1))
            if "dfcite_id" in data and "item_id" in data:
                return data
        except json.JSONDecodeError:
            continue
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
        description="Auto-implement a DFCite relevance summary update as a PR",
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

    # 2. Find the relevance update comment
    relevance_comment = find_relevance_comment(comments)
    if relevance_comment is None:
        print("Error: could not find DFCITE_RELEVANCE_UPDATE preview comment. "
              "Has the issue been previewed?", file=sys.stderr)
        sys.exit(1)

    # 3. Extract JSON block
    data = extract_json_block(relevance_comment["body"])
    if data is None:
        print("Error: no valid JSON block found in the preview comment.",
              file=sys.stderr)
        sys.exit(1)

    item_type = data["item_type"]
    item_id = data["item_id"]
    dfcite_id = data["dfcite_id"]
    relevance_summary = data["relevance_summary_280"]

    # 4. Validate IDs
    validate_item_id(item_id)
    validate_dfcite_id(dfcite_id)

    if item_type not in ("technique", "weakness", "mitigation"):
        print(f"Error: invalid item type: '{item_type}'", file=sys.stderr)
        sys.exit(1)

    # 5. Load and update data file
    type_to_dir = {
        "technique": "techniques",
        "weakness": "weaknesses",
        "mitigation": "mitigations",
    }
    data_dir = os.path.join(project_root, "data", type_to_dir[item_type])
    filepath = os.path.join(data_dir, f"{item_id}.json")

    # Verify the resolved path is inside the expected directory
    real_dir = os.path.realpath(data_dir)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_dir + os.sep):
        print(f"Error: path traversal detected for {item_id}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(filepath):
        print(f"Error: data file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath) as f:
        item_data = json.load(f)

    # Find and update the reference
    references = item_data.get("references", [])
    found = False
    old_relevance = ""
    for ref in references:
        if isinstance(ref, dict) and ref.get("DFCite_id") == dfcite_id:
            old_relevance = ref.get("relevance_summary_280", "")
            ref["relevance_summary_280"] = relevance_summary
            found = True
            break

    if not found:
        print(f"Error: reference {dfcite_id} not found in {item_id}", file=sys.stderr)
        sys.exit(1)

    # Write updated file
    with open(filepath, 'w') as f:
        json.dump(item_data, f, indent=4)
        f.write('\n')

    print(f"Updated {dfcite_id} in {filepath}", file=sys.stderr)

    # 6. Get submitter info
    author_name, author_email = get_submitter_info(issue)
    print(f"Submitter: {author_name} <{author_email}>", file=sys.stderr)

    # 7. Create branch
    branch_name = f"dfcite-relevance/issue-{args.issue_number}-{slugify(dfcite_id)}"

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
        # 8. Commit
        run(["git", "add", filepath], cwd=project_root)

        commit_msg = (
            f"Update DFCite relevance: {dfcite_id} in {item_id}\n\n"
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

        pr_title = f"Update DFCite relevance: {dfcite_id} in {item_id}"

        item_name = item_data.get("name", "")
        ref_corpus = load_reference_corpus(project_root)
        citation_text = ref_corpus.get(dfcite_id, "")
        pr_lines = []
        pr_lines.append("> **This PR was auto-generated** from a DFCite relevance "
                        "update submission. Please review before merging.")
        pr_lines.append("")
        pr_lines.append("## Summary")
        pr_lines.append("")
        pr_lines.append(f"Updates the relevance summary for `{dfcite_id}` in "
                        f"`{item_id}` ({item_name}).")
        pr_lines.append("")
        pr_lines.append("| Field | Value |")
        pr_lines.append("|---|---|")
        pr_lines.append(f"| Item | `{item_id}` — {item_name} |")
        ref_display = f"`{dfcite_id}` — {citation_text}" if citation_text else f"`{dfcite_id}`"
        pr_lines.append(f"| Reference | {ref_display} |")
        pr_lines.append(f"| Previous summary | {old_relevance or '*(none)*'} |")
        pr_lines.append(f"| New summary | {relevance_summary} ({len(relevance_summary)}/280 chars) |")
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
                "--label", "content: update dfcite relevance",
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
