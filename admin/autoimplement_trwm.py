#!/usr/bin/env python3
"""
Auto-implements a TRWM submission by creating data files and opening a PR.

Finds the assigned-ID preview comment, extracts JSON blocks, writes them
to the appropriate data/ directories, updates solve-it.json with the
technique under the correct objective, and opens a PR attributed to
the original issue submitter.

Supports both new submissions and updates to existing techniques.

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
VALID_ID_RE = re.compile(r'^(DFT|DFW|DFM)-\d{4,6}$')


def run(cmd, **kwargs):
    """Run a command and return its stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        result.check_returncode()
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


def find_assigned_comment(comments, is_update=False):
    """Find the preview comment that has real IDs assigned.

    This is the revised comment posted by assign_trwm_ids.py, identifiable
    by the TRWM_PREVIEW marker AND the 'has been assigned' text.

    For updates where all items have real IDs (no temp IDs needing assignment),
    fall back to the original preview comment.
    """
    # First try: look for the assigned-ID version
    for comment in comments:
        body = comment.get("body", "")
        if "<!-- TRWM_PREVIEW -->" in body and "has been assigned" in body:
            return comment

    # For updates: accept the original preview if it has no placeholder IDs
    if is_update:
        for comment in comments:
            body = comment.get("body", "")
            if "<!-- TRWM_PREVIEW -->" in body:
                # Check the ID map — if empty, no assignment was needed
                map_match = re.search(r'<!-- TRWM_ID_MAP: ({.*?}) -->', body)
                if map_match:
                    id_map = json.loads(map_match.group(1))
                    if not id_map:
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


DFCITE_FILE_RE = re.compile(r'^DFCite-\d{4,6}$')


def extract_refs_map(comment_body):
    """Extract the DFCite → BibTeX map from the assigned preview comment.

    After ``assign_trwm_ids.py`` runs, keys are real DFCite IDs. Returns {}
    if no ``TRWM_REFS_MAP`` marker is present.
    """
    match = re.search(r'<!-- TRWM_REFS_MAP: ({.*?}) -->', comment_body, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    # Guard against unassigned placeholders leaking through
    return {k: v for k, v in data.items() if DFCITE_FILE_RE.match(k)}


def write_reference_file(project_root, cite_id, bibtex_text):
    """Write a .bib file for a newly-assigned DFCite. Returns the path written."""
    if not DFCITE_FILE_RE.match(cite_id):
        raise ValueError(f"Invalid DFCite ID: {cite_id}")
    refs_dir = os.path.join(project_root, "data", "references")
    os.makedirs(refs_dir, exist_ok=True)
    path = os.path.join(refs_dir, f"{cite_id}.bib")
    content = bibtex_text if bibtex_text.endswith("\n") else bibtex_text + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def parse_objective_from_issue(issue_body):
    """Extract the Objective field from the issue body."""
    # GitHub issue forms produce ### Objective\n\nvalue
    match = re.search(r'### Objective\s*\n\s*\n\s*(.+)', issue_body)
    if match:
        return match.group(1).strip()
    return None


def parse_submission_type_from_issue(issue_body):
    """Extract the Submission type field from the issue body.

    Returns 'Update existing technique' or 'New technique' (default).
    """
    match = re.search(r'### Submission type\s*\n\s*\n\s*(.+)', issue_body)
    if match:
        return match.group(1).strip()
    return "New technique"


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


def write_data_file(project_root, item_type, block, allow_overwrite=False):
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

    exists = os.path.exists(filepath)
    if exists and not allow_overwrite:
        print(f"Warning: {filepath} already exists, skipping", file=sys.stderr)
        return None

    with open(filepath, 'w') as f:
        json.dump(block, f, indent=4)
        f.write('\n')

    action = "Updated" if exists else "Written"
    print(f"  {action}: {filepath}", file=sys.stderr)
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

    # 2. Detect submission type
    submission_type = parse_submission_type_from_issue(issue["body"])
    is_update = submission_type == "Update existing technique"
    print(f"Submission type: {submission_type}", file=sys.stderr)

    # 3. Find the assigned-ID comment
    assigned_comment = find_assigned_comment(comments, is_update=is_update)
    if assigned_comment is None:
        print("Error: could not find assigned-ID preview comment. "
              "Has the 'assigned ID' label been processed?", file=sys.stderr)
        sys.exit(1)

    # 3. Extract JSON blocks
    blocks = extract_json_blocks(assigned_comment["body"])
    if not blocks:
        print("Error: no JSON blocks found in the assigned comment.", file=sys.stderr)
        sys.exit(1)

    # Extract newly-assigned DFCite reference content (post-substitution)
    refs_to_write = extract_refs_map(assigned_comment["body"])
    if refs_to_write:
        print(f"New reference files to write: {len(refs_to_write)}", file=sys.stderr)

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
    branch_prefix = "trwm-update" if is_update else "trwm"
    branch_name = f"{branch_prefix}/issue-{args.issue_number}-{slugify(technique_name)}"

    if args.dry_run:
        import tempfile
        import shutil
        dry_run_dir = tempfile.mkdtemp(prefix="trwm-dry-run-")
        # Mirror the data directory structure
        for subdir in ("techniques", "weaknesses", "mitigations"):
            os.makedirs(os.path.join(dry_run_dir, "data", subdir))
        # Copy solve-it.json for testing
        shutil.copy(
            os.path.join(project_root, "data", "solve-it.json"),
            os.path.join(dry_run_dir, "data", "solve-it.json"),
        )
        # For updates, copy existing files so overwrite works in dry-run
        if is_update:
            for block in blocks:
                item_type, _ = classify_block(block)
                if item_type:
                    type_dir = {"technique": "techniques", "weakness": "weaknesses",
                                "mitigation": "mitigations"}[item_type]
                    src = os.path.join(project_root, "data", type_dir, f"{block['id']}.json")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(dry_run_dir, "data", type_dir,
                                                       f"{block['id']}.json"))
        write_root = dry_run_dir
    else:
        write_root = project_root

        # Check if branch already exists locally or remotely and add suffix
        existing = subprocess.run(
            ["git", "branch", "--list", branch_name],
            capture_output=True, text=True, cwd=project_root,
        )
        remote_existing = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            capture_output=True, text=True, cwd=project_root,
        )
        if existing.stdout.strip() or remote_existing.stdout.strip():
            # Append a short numeric suffix
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
        # 8. Write data files
        print("Writing data files...", file=sys.stderr)
        written_files = []

        for block in techniques:
            path = write_data_file(write_root, "technique", block,
                                   allow_overwrite=is_update)
            if path:
                written_files.append(path)

        for block in weaknesses:
            path = write_data_file(write_root, "weakness", block,
                                   allow_overwrite=is_update)
            if path:
                written_files.append(path)

        for block in mitigations:
            path = write_data_file(write_root, "mitigation", block,
                                   allow_overwrite=is_update)
            if path:
                written_files.append(path)

        # 8b. Write new DFCite .bib files for freshly-minted references
        for cite_id, bibtex in refs_to_write.items():
            path = write_reference_file(write_root, cite_id, bibtex)
            written_files.append(path)

        # 9. Update solve-it.json (skip for updates — technique already assigned)
        if objective_name and techniques and not is_update:
            if update_solve_it_json(write_root, objective_name, technique_id):
                solve_it_path = os.path.join(write_root, "data", "solve-it.json")
                written_files.append(solve_it_path)

        if not written_files:
            print("No files written — nothing to commit.", file=sys.stderr)
            sys.exit(1)

        if args.dry_run:
            action_word = "updated/created" if is_update else "created"
            print(f"\n=== DRY RUN RESULTS ===", file=sys.stderr)
            print(f"Submission type: {submission_type}", file=sys.stderr)
            print(f"Branch would be: {branch_name}", file=sys.stderr)
            print(f"Author: {author_name} <{author_email}>", file=sys.stderr)
            print(f"Files written to: {dry_run_dir}", file=sys.stderr)
            print(f"\nFiles that would be {action_word}:", file=sys.stderr)
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

        verb = "Update" if is_update else "Add"
        commit_extras = (
            f", {len(refs_to_write)} reference(s)" if refs_to_write else ""
        )
        commit_msg = (
            f"{verb} TRWM submission: {technique_name} ({technique_id})\n\n"
            f"Auto-implemented from issue #{args.issue_number}.\n\n"
            f"Includes {len(techniques)} technique(s), {len(weaknesses)} weakness(es), "
            f"{len(mitigations)} mitigation(s){commit_extras}."
        )

        run([
            "git", "commit",
            "--author", f"{author_name} <{author_email}>",
            "-m", commit_msg,
        ], cwd=project_root)

        # 11. Push and create PR
        print("Pushing branch...", file=sys.stderr)
        run(["git", "push", "-u", "origin", branch_name], cwd=project_root)

        pr_title = f"{verb} TRWM submission: {technique_name} ({technique_id})"

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
        pr_lines.append(f"| Weaknesses | {len(weaknesses)} | see below |")
        pr_lines.append(f"| Mitigations | {len(mitigations)} | see below |")
        if refs_to_write:
            pr_lines.append(f"| References (new DFCites) | {len(refs_to_write)} | see below |")
        if objective_name:
            pr_lines.append(f"| Objective | — | {objective_name} |")
        pr_lines.append("")

        # List of files created/updated
        files_header = "Files updated/created" if is_update else "Files"
        pr_lines.append(f"## {files_header}")
        pr_lines.append("")
        for f in written_files:
            # Show path relative to repo root
            rel = os.path.relpath(f, project_root)
            pr_lines.append(f"- `{rel}`")
        pr_lines.append("")

        # Weakness details
        if weaknesses:
            pr_lines.append("## Weaknesses")
            pr_lines.append("")
            pr_lines.append("| ID | Name | ASTM classes |")
            pr_lines.append("|---|---|---|")
            for w in weaknesses:
                classes = w.get("categories", [])
                flags_str = ", ".join(c.replace("ASTM_", "") for c in classes) if classes else "—"
                pr_lines.append(f"| `{w['id']}` | {w['name']} | {flags_str} |")
            pr_lines.append("")

        # Mitigation details
        if mitigations:
            pr_lines.append("## Mitigations")
            pr_lines.append("")
            pr_lines.append("| ID | Name |")
            pr_lines.append("|---|---|")
            for m in mitigations:
                pr_lines.append(f"| `{m['id']}` | {m['name']} |")
            pr_lines.append("")

        # Newly minted DFCite references
        if refs_to_write:
            pr_lines.append("## New references")
            pr_lines.append("")
            pr_lines.append("The following `.bib` files were created for citations "
                            "submitted as bare BibTeX and approved during review:")
            pr_lines.append("")
            for cite_id in sorted(refs_to_write.keys()):
                pr_lines.append(f"- `data/references/{cite_id}.bib`")
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
        pr_lines.append("")
        pr_lines.append(f"Resolves #{args.issue_number}")

        pr_body = '\n'.join(pr_lines)

        # Write PR body to a temp file to avoid command-line length limits
        pr_body_file = os.path.join(project_root, ".pr_body.md")
        with open(pr_body_file, 'w') as f:
            f.write(pr_body)

        try:
            pr_url = run([
                "gh", "pr", "create",
                "--head", branch_name,
                "--title", pr_title,
                "--body-file", pr_body_file,
                "--label", "trwm",
                "--label", "autoimplement",
            ], cwd=project_root)
        finally:
            if os.path.exists(pr_body_file):
                os.remove(pr_body_file)

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
