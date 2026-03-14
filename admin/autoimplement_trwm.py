#!/usr/bin/env python3
"""
Auto-implements a TRWM submission by creating data files and opening a PR.

Finds the assigned-ID preview comment, extracts JSON blocks, writes them
to the appropriate data/ directories, updates solve-it.json with the
technique under the correct objective, and opens a PR attributed to
the original issue submitter.

Only supports new submissions (not updates).

Usage:
    python3 admin/autoimplement_trwm.py --issue-number 328
"""

import argparse
import json
import os
import re
import subprocess
import sys


# Strict ID patterns — only allow expected format to prevent path traversal
VALID_ID_RE = re.compile(r'^(DFT|DFW|DFM)-\d{4,5}$')


def run(cmd, **kwargs):
    """Run a command and return its stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, **kwargs)
    return result.stdout.strip()


def validate_id(item_id):
    """Validate that an ID matches the expected format (e.g. DFT-1176).

    Prevents path traversal via crafted IDs.
    """
    if not VALID_ID_RE.match(item_id):
        print(f"Error: invalid ID format: '{item_id}'", file=sys.stderr)
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


def find_assigned_comment(comments):
    """Find the preview comment that has real IDs assigned.

    This is the revised comment posted by assign_trwm_ids.py, identifiable
    by the TRWM_PREVIEW marker AND the 'has been assigned' text.
    """
    for comment in comments:
        body = comment.get("body", "")
        if "<!-- TRWM_PREVIEW -->" in body and "has been assigned" in body:
            return comment
    return None


def extract_json_blocks(comment_body):
    """Extract all JSON code blocks from the comment body.

    Returns a list of parsed dicts, each with an 'id' field.
    """
    blocks = []
    pattern = re.compile(r'```json\s*\n(.*?)\n```', re.DOTALL)
    for match in pattern.finditer(comment_body):
        try:
            data = json.loads(match.group(1))
            if "id" in data:
                blocks.append(data)
        except json.JSONDecodeError:
            continue
    return blocks


def parse_objective_from_issue(issue_body):
    """Extract the Objective field from the issue body."""
    # GitHub issue forms produce ### Objective\n\nvalue
    match = re.search(r'### Objective\s*\n\s*\n\s*(.+)', issue_body)
    if match:
        return match.group(1).strip()
    return None


def classify_block(block):
    """Classify a JSON block by its ID prefix.

    Returns ('technique', 'weakness', or 'mitigation', id_string).
    """
    item_id = block["id"]
    if item_id.startswith("DFT-"):
        return "technique", item_id
    elif item_id.startswith("DFW-"):
        return "weakness", item_id
    elif item_id.startswith("DFM-"):
        return "mitigation", item_id
    return None, item_id


def write_data_file(project_root, item_type, block):
    """Write a JSON block to the appropriate data directory."""
    validate_id(block["id"])

    type_to_dir = {
        "technique": "techniques",
        "weakness": "weaknesses",
        "mitigation": "mitigations",
    }
    directory = os.path.join(project_root, "data", type_to_dir[item_type])
    filepath = os.path.join(directory, f"{block['id']}.json")

    # Verify the resolved path is inside the expected directory
    real_dir = os.path.realpath(directory)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_dir + os.sep):
        print(f"Error: path traversal detected for {block['id']}", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(filepath):
        print(f"Warning: {filepath} already exists, skipping", file=sys.stderr)
        return None

    with open(filepath, 'w') as f:
        json.dump(block, f, indent=4)
        f.write('\n')

    print(f"  Written: {filepath}", file=sys.stderr)
    return filepath


def update_solve_it_json(project_root, objective_name, technique_id):
    """Add the technique ID to the correct objective in solve-it.json."""
    filepath = os.path.join(project_root, "data", "solve-it.json")

    with open(filepath) as f:
        objectives = json.load(f)

    found = False
    for objective in objectives:
        if objective["name"] == objective_name:
            if technique_id not in objective["techniques"]:
                objective["techniques"].append(technique_id)
                found = True
                print(f"  Added {technique_id} to objective '{objective_name}'",
                      file=sys.stderr)
            else:
                print(f"  {technique_id} already in objective '{objective_name}'",
                      file=sys.stderr)
                found = True
            break

    if not found:
        print(f"Warning: objective '{objective_name}' not found in solve-it.json",
              file=sys.stderr)
        return False

    with open(filepath, 'w') as f:
        json.dump(objectives, f, indent=4)
        f.write('\n')

    return True


def sanitise_git_value(value):
    """Remove characters that could cause issues in git --author strings."""
    # Strip angle brackets (used as delimiters) and newlines
    return re.sub(r'[<>\n\r]', '', value).strip()


def get_submitter_info(issue):
    """Get the original submitter's name and noreply email for commit attribution."""
    user = issue["user"]
    login = user["login"]
    user_id = user["id"]

    # Fetch full user profile for their name
    raw = run(["gh", "api", f"users/{login}"])
    profile = json.loads(raw)
    name = sanitise_git_value(profile.get("name") or login)

    # Use GitHub's noreply email format (login is already validated by GitHub)
    email = f"{user_id}+{login}@users.noreply.github.com"

    return name, email


def slugify(text, max_len=50):
    """Create a branch-safe slug from text."""
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return slug[:max_len].rstrip('-')


def main():
    parser = argparse.ArgumentParser(
        description="Auto-implement a TRWM submission as a PR",
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
        help="Write files and show what would happen, but don't commit, push, or create PR",
    )
    args = parser.parse_args()

    project_root = args.project_root
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Fetch issue and comments
    print("Fetching issue...", file=sys.stderr)
    issue = get_issue(args.issue_number)
    comments = get_issue_comments(args.issue_number)

    # 2. Find the assigned-ID comment
    assigned_comment = find_assigned_comment(comments)
    if assigned_comment is None:
        print("Error: could not find assigned-ID preview comment. "
              "Has the 'assigned ID' label been processed?", file=sys.stderr)
        sys.exit(1)

    # 3. Extract JSON blocks
    blocks = extract_json_blocks(assigned_comment["body"])
    if not blocks:
        print("Error: no JSON blocks found in the assigned comment.", file=sys.stderr)
        sys.exit(1)

    # Classify blocks
    techniques = []
    weaknesses = []
    mitigations = []
    for block in blocks:
        item_type, item_id = classify_block(block)
        if item_type == "technique":
            techniques.append(block)
        elif item_type == "weakness":
            weaknesses.append(block)
        elif item_type == "mitigation":
            mitigations.append(block)

    print(f"Found: {len(techniques)} techniques, {len(weaknesses)} weaknesses, "
          f"{len(mitigations)} mitigations", file=sys.stderr)

    # 4. Get objective from issue body
    objective_name = parse_objective_from_issue(issue["body"])
    if not objective_name or objective_name == "Other (specify below)":
        # Check for proposed new objective
        match = re.search(r'### Propose new objective\s*\n\s*\n\s*(.+)', issue["body"])
        if match and match.group(1).strip() != "_No response_":
            objective_name = match.group(1).strip()
            print(f"Warning: new objective proposed: '{objective_name}'. "
                  "solve-it.json will NOT be updated — add the objective manually.",
                  file=sys.stderr)
            objective_name = None
        else:
            print("Warning: no objective found. solve-it.json will NOT be updated.",
                  file=sys.stderr)
            objective_name = None

    # 5. Get submitter info for attribution
    author_name, author_email = get_submitter_info(issue)
    print(f"Submitter: {author_name} <{author_email}>", file=sys.stderr)

    # 6. Validate all IDs upfront before creating branch
    for block in blocks:
        validate_id(block["id"])

    # 7. Write data files to a temp directory in dry-run mode, or to the repo
    technique_name = techniques[0]["name"] if techniques else f"issue-{args.issue_number}"
    technique_id = techniques[0]["id"] if techniques else "TRWM"
    branch_name = f"trwm/issue-{args.issue_number}-{slugify(technique_name)}"

    if args.dry_run:
        import tempfile
        dry_run_dir = tempfile.mkdtemp(prefix="trwm-dry-run-")
        # Mirror the data directory structure
        for subdir in ("techniques", "weaknesses", "mitigations"):
            os.makedirs(os.path.join(dry_run_dir, "data", subdir))
        # Copy solve-it.json for testing
        import shutil
        shutil.copy(
            os.path.join(project_root, "data", "solve-it.json"),
            os.path.join(dry_run_dir, "data", "solve-it.json"),
        )
        write_root = dry_run_dir
    else:
        write_root = project_root
        print(f"Creating branch: {branch_name}", file=sys.stderr)
        run(["git", "checkout", "-b", branch_name], cwd=project_root)

    try:
        # 8. Write data files
        print("Writing data files...", file=sys.stderr)
        written_files = []

        for block in techniques:
            path = write_data_file(write_root, "technique", block)
            if path:
                written_files.append(path)

        for block in weaknesses:
            path = write_data_file(write_root, "weakness", block)
            if path:
                written_files.append(path)

        for block in mitigations:
            path = write_data_file(write_root, "mitigation", block)
            if path:
                written_files.append(path)

        # 9. Update solve-it.json
        if objective_name and techniques:
            if update_solve_it_json(write_root, objective_name, technique_id):
                solve_it_path = os.path.join(write_root, "data", "solve-it.json")
                written_files.append(solve_it_path)

        if not written_files:
            print("No files written — nothing to commit.", file=sys.stderr)
            sys.exit(1)

        if args.dry_run:
            print(f"\n=== DRY RUN RESULTS ===", file=sys.stderr)
            print(f"Branch would be: {branch_name}", file=sys.stderr)
            print(f"Author: {author_name} <{author_email}>", file=sys.stderr)
            print(f"Files written to: {dry_run_dir}", file=sys.stderr)
            print(f"\nFiles that would be created:", file=sys.stderr)
            for f in written_files:
                print(f"  {f}", file=sys.stderr)
            print(f"\nTo inspect:", file=sys.stderr)
            print(f"  ls {dry_run_dir}/data/techniques/", file=sys.stderr)
            print(f"  ls {dry_run_dir}/data/weaknesses/", file=sys.stderr)
            print(f"  ls {dry_run_dir}/data/mitigations/", file=sys.stderr)
            return

        # 10. Commit with original submitter as author
        for f in written_files:
            run(["git", "add", f], cwd=project_root)

        commit_msg = (
            f"Add TRWM submission: {technique_name} ({technique_id})\n\n"
            f"Auto-implemented from issue #{args.issue_number}.\n\n"
            f"Includes {len(techniques)} technique(s), {len(weaknesses)} weakness(es), "
            f"{len(mitigations)} mitigation(s)."
        )

        run([
            "git", "commit",
            "--author", f"{author_name} <{author_email}>",
            "-m", commit_msg,
        ], cwd=project_root)

        # 11. Push and create PR
        print("Pushing branch...", file=sys.stderr)
        run(["git", "push", "-u", "origin", branch_name], cwd=project_root)

        pr_title = f"Add TRWM submission: {technique_name} ({technique_id})"

        # Build detailed PR body
        pr_lines = []
        pr_lines.append("> **This PR was auto-generated** from a TRWM submission. "
                        "Please review the files below before merging.")
        pr_lines.append("")
        pr_lines.append(f"## Summary")
        pr_lines.append("")
        pr_lines.append(f"Implements the TRWM submission from #{args.issue_number}.")
        pr_lines.append("")
        pr_lines.append(f"| | Count | Details |")
        pr_lines.append(f"|---|---|---|")
        t = techniques[0]
        pr_lines.append(f"| Technique | {len(techniques)} | "
                        f"`{t['id']}` — {t['name']} |")
        w_ids = ', '.join('`' + w['id'] + '`' for w in weaknesses)
        pr_lines.append(f"| Weaknesses | {len(weaknesses)} | {w_ids} |")
        m_ids = ', '.join('`' + m['id'] + '`' for m in mitigations)
        pr_lines.append(f"| Mitigations | {len(mitigations)} | {m_ids} |")
        if objective_name:
            pr_lines.append(f"| Objective | — | {objective_name} |")
        pr_lines.append("")

        # List of files created
        pr_lines.append("## Files")
        pr_lines.append("")
        for f in written_files:
            # Show path relative to repo root
            rel = os.path.relpath(f, project_root)
            pr_lines.append(f"- `{rel}`")
        pr_lines.append("")

        # Existing KB references
        # Collect real IDs referenced in weaknesses' mitigation lists
        existing_refs = set()
        for w in weaknesses:
            for mid in w.get("mitigations", []):
                if VALID_ID_RE.match(mid) and not any(
                    m["id"] == mid for m in mitigations
                ):
                    existing_refs.add(mid)
        if existing_refs:
            pr_lines.append("## Existing KB references")
            pr_lines.append("")
            pr_lines.append("These existing items are referenced by the new weaknesses "
                            "(not modified by this PR):")
            pr_lines.append("")
            for ref_id in sorted(existing_refs):
                pr_lines.append(f"- `{ref_id}`")
            pr_lines.append("")

        pr_lines.append("## Attribution")
        pr_lines.append("")
        pr_lines.append(f"Original submission by @{issue['user']['login']} "
                        f"in #{args.issue_number}.")
        pr_lines.append(f"Commit authored as: {author_name} <{author_email}>")

        pr_body = '\n'.join(pr_lines)

        pr_url = run([
            "gh", "pr", "create",
            "--title", pr_title,
            "--body", pr_body,
        ])

        print(f"PR created: {pr_url}", file=sys.stderr)

        # 12. Post a comment on the original issue linking to the PR
        link_comment = f"PR created: {pr_url}"
        run(["gh", "issue", "comment", str(args.issue_number), "--body", link_comment])

        print(pr_url)

    except Exception as e:
        if not args.dry_run:
            # Clean up: switch back to previous branch so the runner isn't left
            # on a half-finished branch
            print(f"Error during implementation: {e}", file=sys.stderr)
            subprocess.run(["git", "checkout", "-"], cwd=project_root,
                           capture_output=True, text=True)
        raise


if __name__ == "__main__":
    main()
