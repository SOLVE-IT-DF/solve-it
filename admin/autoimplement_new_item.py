#!/usr/bin/env python3
"""
Auto-implements a new technique, weakness, or mitigation by creating a data
file and opening a PR.

Finds the assigned-ID comment (the revised preview comment posted by the
assign_{type}_id.py script), extracts the JSON block, writes it to the
appropriate data/ directory, updates solve-it.json for techniques, and
opens a PR attributed to the original issue submitter.

Handles both DFCite-format references (dicts with DFCite_id) and old-format
raw string references (matched against the corpus or flagged as PENDING).

Usage:
    python3 admin/autoimplement_new_item.py --issue-number 279
"""

import argparse
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote, urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solve_it_library.reference_matching import (
    load_reference_corpus,
    match_reference,
)


# Strict ID patterns — only allow expected format to prevent path traversal
VALID_ID_RE = re.compile(r'^(DFT|DFW|DFM)-\d{4,6}$')
VALID_DFCITE_RE = re.compile(r'^DFCite-\d{4,6}$')

# Old-format IDs (T1234, W1234, M1234) used before the DFT-/DFW-/DFM- convention
OLD_ID_RE = re.compile(r'^([TWM])(\d{4,6})$')
OLD_PREFIX_MAP = {"T": "DFT", "W": "DFW", "M": "DFM"}


def run(cmd, **kwargs):
    """Run a command and return its stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"stderr: {result.stderr}", file=sys.stderr)
        result.check_returncode()
    return result.stdout.strip()


def normalize_id(item_id):
    """Convert old-format IDs (T1234, W1234, M1234) to new format (DFT-1234, etc.).

    Returns the ID unchanged if already in new format, or None if invalid.
    """
    if VALID_ID_RE.match(item_id):
        return item_id
    old_match = OLD_ID_RE.match(item_id)
    if old_match:
        prefix = OLD_PREFIX_MAP[old_match.group(1)]
        return f"{prefix}-{old_match.group(2)}"
    return None


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


def _comment_has_real_id(body):
    """Check if a comment body contains a JSON block with a real (non-placeholder) ID."""
    pattern = re.compile(r'```json\s*\n(.*?)\n```', re.DOTALL)
    for match in pattern.finditer(body):
        try:
            data = json.loads(match.group(1))
            if "id" in data:
                raw_id = data["id"]
                if VALID_ID_RE.match(raw_id) or OLD_ID_RE.match(raw_id):
                    return True
        except json.JSONDecodeError:
            continue
    return False


def find_assigned_comment(comments):
    """Find the comment with the assigned (real) ID.

    The assign_{type}_id.py scripts post a revised preview comment with text
    like "has been assigned" after replacing the placeholder ID. We look for
    that revised comment. The comment also contains a JSON code block with
    the real ID.

    Search strategy (in order):
    1. Comment with "has been assigned" text AND a JSON block with a real ID
    2. Fallback: last comment with a JSON block containing a real ID
       (covers older issues where the header text wasn't updated)

    Handles both new-format IDs (DFT-1234) and old-format IDs (T1234).
    """
    # Primary: look for the "has been assigned" text with a JSON block
    for comment in comments:
        body = comment.get("body", "")
        if "has been assigned" in body and _comment_has_real_id(body):
            return comment

    # Fallback: last comment with a real ID in a JSON block
    # (iterate in reverse so we get the most recent one)
    for comment in reversed(comments):
        body = comment.get("body", "")
        if _comment_has_real_id(body):
            return comment

    return None


def extract_json_block(comment_body):
    """Extract the JSON code block from the comment body.

    Returns the parsed dict with an 'id' field. If the ID is in old format
    (T1234, W1234, M1234), it is normalized to new format (DFT-1234, etc.).
    """
    pattern = re.compile(r'```json\s*\n(.*?)\n```', re.DOTALL)
    for match in pattern.finditer(comment_body):
        try:
            data = json.loads(match.group(1))
            if "id" in data:
                normalized = normalize_id(data["id"])
                if normalized:
                    data["id"] = normalized
                return data
        except json.JSONDecodeError:
            continue
    return None


def classify_type(item_id):
    """Classify item type from ID prefix.

    Returns 'technique', 'weakness', or 'mitigation'.
    """
    if item_id.startswith("DFT-"):
        return "technique"
    elif item_id.startswith("DFW-"):
        return "weakness"
    elif item_id.startswith("DFM-"):
        return "mitigation"
    return None


def handle_old_format_references(block, project_root):
    """Convert old-format raw string references to DFCite format.

    Old issues may have references as a list of strings instead of
    the current dict format with DFCite_id and relevance_summary_280.

    Returns (updated_refs, warnings, unmatched_raw_refs) where warnings
    describe any references that couldn't be matched, and
    unmatched_raw_refs is a list of the original raw strings that failed.
    """
    refs = block.get("references", [])
    if not refs:
        return refs, [], []

    # Check if refs are already in dict format
    if all(isinstance(r, dict) for r in refs):
        return refs, [], []

    corpus = load_reference_corpus(project_root)
    updated_refs = []
    warnings = []
    unmatched_raw_refs = []

    for ref in refs:
        if isinstance(ref, dict):
            # Already in dict format, keep as-is
            updated_refs.append(ref)
            continue

        # Raw string reference — try to match
        ref_str = str(ref).strip()
        if not ref_str:
            continue

        result = match_reference(ref_str, corpus)
        if result:
            cite_id, match_type = result
            updated_refs.append({
                "DFCite_id": cite_id,
                "relevance_summary_280": "",
            })
        else:
            # Can't match — use PENDING placeholder
            updated_refs.append({
                "DFCite_id": "PENDING",
                "relevance_summary_280": "",
            })
            unmatched_raw_refs.append(ref_str)
            truncated = ref_str[:80] + ("..." if len(ref_str) > 80 else "")
            warnings.append(
                f'Could not match reference: "{truncated}". '
                f'A DFCite entry needs to be created first via the reference form.'
            )

    return updated_refs, warnings, unmatched_raw_refs


def check_dfcite_existence(block, project_root):
    """Check that all DFCite IDs referenced in the block actually exist.

    Returns a list of warning strings for missing DFCite files.
    """
    refs = block.get("references", [])
    warnings = []
    refs_dir = os.path.join(project_root, "data", "references")

    for ref in refs:
        if not isinstance(ref, dict):
            continue
        cite_id = ref.get("DFCite_id", "")
        if cite_id == "PENDING" or not cite_id:
            continue
        if not VALID_DFCITE_RE.match(cite_id):
            continue
        txt_path = os.path.join(refs_dir, f"{cite_id}.txt")
        bib_path = os.path.join(refs_dir, f"{cite_id}.bib")
        if not os.path.exists(txt_path) and not os.path.exists(bib_path):
            warnings.append(
                f'Referenced `{cite_id}` does not exist in `data/references/`. '
                f'It may need to be created via a separate reference proposal.'
            )

    return warnings


REPO_URL = "https://github.com/SOLVE-IT-DF/solve-it"
REFERENCE_TEMPLATE = "1d_propose-new-reference-form.yml"


def summarise_citation(raw_citation_text):
    """Extract 'Author (Year) Short title' from a raw citation string.

    Best-effort — falls back to a truncated version of the raw text.
    """
    text = raw_citation_text.strip()

    # Try to extract surname (first word before comma) and a 4-digit year
    surname_match = re.match(r'([A-Za-z\-]+)', text)
    year_match = re.search(r'\b((?:19|20)\d{2})\b', text)

    surname = surname_match.group(1) if surname_match else None
    year = year_match.group(1) if year_match else None

    # Try to find a title-like segment after the year or after author block.
    # Common patterns: "...2015. Title here." or "...2015, May. Title here."
    title_snippet = None
    if year_match:
        after_year = text[year_match.end():]
        # Skip punctuation, month names, "May.", "In " etc.
        title_match = re.search(r'[.,:;]\s*(?:(?:January|February|March|April|May|'
                                r'June|July|August|September|October|November|December)'
                                r'[.,:;]?\s*)?(.{10,})', after_year, re.IGNORECASE)
        if title_match:
            title_snippet = title_match.group(1).strip()
            # Take up to the next period or 60 chars
            period_pos = title_snippet.find('.')
            if period_pos > 10:
                title_snippet = title_snippet[:period_pos]
            else:
                title_snippet = title_snippet[:60].rstrip()

    parts = []
    if surname:
        parts.append(surname)
    if year:
        parts.append(f"({year})")
    if title_snippet:
        parts.append(title_snippet)

    if parts:
        return ' '.join(parts)

    # Fallback: truncated raw text
    return text[:60].rstrip()


def build_reference_form_url(raw_citation_text, issue_number, item_id):
    """Build a pre-filled URL for the 'Propose New Reference' issue form."""
    summary = summarise_citation(raw_citation_text)
    params = {
        "template": REFERENCE_TEMPLATE,
        "title": f"Propose new reference: {summary}",
        "citation-text": raw_citation_text,
        "notes": f"Required by issue #{issue_number} for {item_id}",
    }
    return f"{REPO_URL}/issues/new?{urlencode(params, quote_via=quote)}"


def post_blocked_comment_and_remove_label(issue_number, item_id, unmatched_raw_refs,
                                          dfcite_warnings):
    """Post an explanatory comment on the issue and remove the autoimplement label.

    Called when autoimplement cannot proceed because of missing DFCite references.
    """
    lines = []
    lines.append("### Autoimplement blocked: missing DFCite references")
    lines.append("")

    if unmatched_raw_refs:
        lines.append("**Unmatched references (need new DFCite entries):**")
        lines.append("")
        for raw_ref in unmatched_raw_refs:
            truncated = raw_ref[:80] + ("..." if len(raw_ref) > 80 else "")
            url = build_reference_form_url(raw_ref, issue_number, item_id)
            lines.append(f'- "{truncated}" \u2014 [Create DFCite entry]({url})')
        lines.append("")

    if dfcite_warnings:
        lines.append("**Missing DFCite files:**")
        lines.append("")
        for w in dfcite_warnings:
            # Extract the DFCite ID from the warning string
            m = re.search(r'`(DFCite-\d+)`', w)
            cite_id = m.group(1) if m else "unknown"
            lines.append(f"- `{cite_id}` does not exist in `data/references/`")
        lines.append("")

    lines.append("**Next steps:**")
    lines.append("1. Click the link(s) above to propose the missing reference(s)")
    lines.append("2. Wait for the reference PR(s) to be merged")
    lines.append("3. Re-add the `autoimplement` label to this issue")

    comment_body = "\n".join(lines)

    # Post the comment
    run(["gh", "issue", "comment", str(issue_number), "--body", comment_body])

    # Remove the autoimplement label
    run(["gh", "issue", "edit", str(issue_number), "--remove-label", "autoimplement"])

    print(f"Posted blocked comment and removed autoimplement label on #{issue_number}",
          file=sys.stderr)


def parse_objective_from_issue(issue_body):
    """Extract the Objective field from the issue body."""
    match = re.search(r'### Objective\s*\n\s*\n\s*(.+)', issue_body)
    if match:
        return match.group(1).strip()
    return None


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


def update_technique_weaknesses(project_root, technique_id, weakness_id):
    """Add a weakness ID to a technique's weaknesses list.

    Returns (filepath_or_None, warning_or_None).
    """
    if not VALID_ID_RE.match(technique_id):
        return None, f"Invalid technique ID format: '{technique_id}'"

    filepath = os.path.join(project_root, "data", "techniques", f"{technique_id}.json")

    # Path traversal protection
    real_dir = os.path.realpath(os.path.join(project_root, "data", "techniques"))
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_dir + os.sep):
        return None, f"Path traversal detected for {technique_id}"

    if not os.path.exists(filepath):
        return None, f"Technique file `{technique_id}.json` not found — cannot auto-add weakness"

    with open(filepath) as f:
        data = json.load(f)

    if weakness_id in data.get("weaknesses", []):
        print(f"  {weakness_id} already in {technique_id}'s weaknesses list", file=sys.stderr)
        return None, None

    if "weaknesses" not in data:
        data["weaknesses"] = []
    data["weaknesses"].append(weakness_id)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        f.write('\n')

    print(f"  Added {weakness_id} to {technique_id}'s weaknesses list", file=sys.stderr)
    return filepath, None


def update_weakness_mitigations(project_root, weakness_id, mitigation_id):
    """Add a mitigation ID to a weakness's mitigations list.

    Returns (filepath_or_None, warning_or_None).
    """
    if not VALID_ID_RE.match(weakness_id):
        return None, f"Invalid weakness ID format: '{weakness_id}'"

    filepath = os.path.join(project_root, "data", "weaknesses", f"{weakness_id}.json")

    # Path traversal protection
    real_dir = os.path.realpath(os.path.join(project_root, "data", "weaknesses"))
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_dir + os.sep):
        return None, f"Path traversal detected for {weakness_id}"

    if not os.path.exists(filepath):
        return None, f"Weakness file `{weakness_id}.json` not found — cannot auto-add mitigation"

    with open(filepath) as f:
        data = json.load(f)

    if mitigation_id in data.get("mitigations", []):
        print(f"  {mitigation_id} already in {weakness_id}'s mitigations list", file=sys.stderr)
        return None, None

    if "mitigations" not in data:
        data["mitigations"] = []
    data["mitigations"].append(mitigation_id)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        f.write('\n')

    print(f"  Added {mitigation_id} to {weakness_id}'s mitigations list", file=sys.stderr)
    return filepath, None


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


def find_cross_references(block, item_type, parent_update_warnings=None):
    """Find cross-references that need manual attention.

    Returns a list of human-readable notes about cross-references.
    Parent updates that succeeded are no longer listed; only failed/skipped
    parent updates (from parent_update_warnings) are included.
    """
    notes = []
    item_id = block["id"]

    # Add any parent update failures as manual steps
    if parent_update_warnings:
        notes.extend(parent_update_warnings)

    if item_type == "weakness":
        # Mitigations referenced by this weakness — note for manual check
        for mid in block.get("mitigations", []):
            if VALID_ID_RE.match(mid):
                notes.append(f"Add `{item_id}` to `{mid}`'s weaknesses list (if applicable)")
    elif item_type == "technique":
        # Techniques may reference weaknesses
        for wid in block.get("weaknesses", []):
            if VALID_ID_RE.match(wid):
                notes.append(f"Verify `{wid}` exists and references `{item_id}` if needed")

    return notes


def main():
    parser = argparse.ArgumentParser(
        description="Auto-implement a new technique/weakness/mitigation as a PR",
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
        print("Error: could not find assigned-ID comment. "
              "Has the ID been assigned?", file=sys.stderr)
        sys.exit(1)

    # 3. Extract JSON block
    block = extract_json_block(assigned_comment["body"])
    if block is None:
        print("Error: no JSON block found in the assigned comment.", file=sys.stderr)
        sys.exit(1)

    item_id = block["id"]
    validate_id(item_id)
    item_type = classify_type(item_id)
    if item_type is None:
        print(f"Error: unrecognised ID prefix in '{item_id}'", file=sys.stderr)
        sys.exit(1)

    item_name = block.get("name", item_id)
    print(f"Found {item_type}: {item_id} ({item_name})", file=sys.stderr)

    # 4. Handle old-format references
    all_warnings = []
    block["references"], ref_warnings, unmatched_raw_refs = handle_old_format_references(
        block, project_root)
    all_warnings.extend(ref_warnings)

    # 5. Check existing DFCite refs
    dfcite_warnings = check_dfcite_existence(block, project_root)
    all_warnings.extend(dfcite_warnings)

    if all_warnings:
        print("Warnings:", file=sys.stderr)
        for w in all_warnings:
            print(f"  - {w}", file=sys.stderr)

    # 5b. Abort if there are unresolved references
    has_pending = any(
        isinstance(r, dict) and r.get("DFCite_id") == "PENDING"
        for r in block.get("references", [])
    )
    if has_pending or dfcite_warnings:
        if args.dry_run:
            print("\n=== DRY RUN: Would abort ===", file=sys.stderr)
            print(f"Item: {item_type} {item_id} ({item_name})", file=sys.stderr)
            if unmatched_raw_refs:
                print("Unmatched references:", file=sys.stderr)
                for raw in unmatched_raw_refs:
                    url = build_reference_form_url(raw, args.issue_number, item_id)
                    truncated = raw[:80] + ("..." if len(raw) > 80 else "")
                    print(f'  - "{truncated}"', file=sys.stderr)
                    print(f'    Create: {url}', file=sys.stderr)
            if dfcite_warnings:
                print("Missing DFCite files:", file=sys.stderr)
                for w in dfcite_warnings:
                    print(f"  - {w}", file=sys.stderr)
            print("Would post blocked comment and remove autoimplement label.",
                  file=sys.stderr)
            return
        else:
            post_blocked_comment_and_remove_label(
                args.issue_number, item_id, unmatched_raw_refs, dfcite_warnings)
            return

    # 6. Get objective from issue body (techniques only)
    objective_name = None
    if item_type == "technique":
        objective_name = parse_objective_from_issue(issue["body"])
        if not objective_name or objective_name == "Other (specify below)":
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

    # 7. Get submitter info for attribution
    author_name, author_email = get_submitter_info(issue)
    print(f"Submitter: {author_name} <{author_email}>", file=sys.stderr)

    # 8. Create branch and write files
    type_labels = {"technique": "technique", "weakness": "weakness", "mitigation": "mitigation"}
    branch_name = f"new-{type_labels[item_type]}/issue-{args.issue_number}-{slugify(item_name)}"

    if args.dry_run:
        import tempfile
        import shutil
        dry_run_dir = tempfile.mkdtemp(prefix="new-item-dry-run-")
        for subdir in ("techniques", "weaknesses", "mitigations"):
            src_dir = os.path.join(project_root, "data", subdir)
            dst_dir = os.path.join(dry_run_dir, "data", subdir)
            os.makedirs(dst_dir)
            # Copy existing files so parent updates can work in dry-run
            if os.path.isdir(src_dir):
                for fname in os.listdir(src_dir):
                    if fname.endswith('.json'):
                        shutil.copy(
                            os.path.join(src_dir, fname),
                            os.path.join(dst_dir, fname),
                        )
        shutil.copy(
            os.path.join(project_root, "data", "solve-it.json"),
            os.path.join(dry_run_dir, "data", "solve-it.json"),
        )
        write_root = dry_run_dir
    else:
        write_root = project_root

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
        # 9. Strip autoimplement metadata before writing data file
        parent_techniques = block.pop("_parent_techniques", [])
        parent_weaknesses = block.pop("_parent_weaknesses", [])

        # Write data file
        print("Writing data file...", file=sys.stderr)
        filepath = write_data_file(write_root, item_type, block)
        if filepath is None:
            print("Error: file already exists — nothing to commit.", file=sys.stderr)
            sys.exit(1)

        written_files = [filepath]

        # 10. Update solve-it.json for techniques
        if item_type == "technique" and objective_name:
            if update_solve_it_json(write_root, objective_name, item_id):
                solve_it_path = os.path.join(write_root, "data", "solve-it.json")
                written_files.append(solve_it_path)

        # 10b. Update parent items
        parent_update_warnings = []

        if item_type == "weakness":
            for tid in parent_techniques:
                normalized = normalize_id(tid)
                if not normalized:
                    parent_update_warnings.append(
                        f"Could not update parent technique `{tid}` — invalid ID format")
                    continue
                fpath, warning = update_technique_weaknesses(write_root, normalized, item_id)
                if fpath:
                    written_files.append(fpath)
                if warning:
                    parent_update_warnings.append(warning)

        if item_type == "mitigation":
            for wid in parent_weaknesses:
                normalized = normalize_id(wid)
                if not normalized:
                    parent_update_warnings.append(
                        f"Could not update parent weakness `{wid}` — invalid ID format")
                    continue
                fpath, warning = update_weakness_mitigations(write_root, normalized, item_id)
                if fpath:
                    written_files.append(fpath)
                if warning:
                    parent_update_warnings.append(warning)

        all_warnings.extend(parent_update_warnings)

        # 11. Find cross-references for PR body
        cross_refs = find_cross_references(block, item_type, parent_update_warnings)

        if args.dry_run:
            print(f"\n=== DRY RUN RESULTS ===", file=sys.stderr)
            print(f"Item: {item_type} {item_id} ({item_name})", file=sys.stderr)
            print(f"Branch would be: {branch_name}", file=sys.stderr)
            print(f"Author: {author_name} <{author_email}>", file=sys.stderr)
            print(f"Files written to: {write_root}", file=sys.stderr)
            print(f"\nFiles that would be created/updated:", file=sys.stderr)
            for f in written_files:
                print(f"  {f}", file=sys.stderr)
            if parent_techniques:
                print(f"\nParent technique updates:", file=sys.stderr)
                for tid in parent_techniques:
                    normalized = normalize_id(tid) or tid
                    print(f"  Would update technique {normalized}", file=sys.stderr)
            if parent_weaknesses:
                print(f"\nParent weakness updates:", file=sys.stderr)
                for wid in parent_weaknesses:
                    normalized = normalize_id(wid) or wid
                    print(f"  Would update weakness {normalized}", file=sys.stderr)
            if all_warnings:
                print(f"\nWarnings:", file=sys.stderr)
                for w in all_warnings:
                    print(f"  - {w}", file=sys.stderr)
            if cross_refs:
                print(f"\nCross-references (manual steps):", file=sys.stderr)
                for note in cross_refs:
                    print(f"  - {note}", file=sys.stderr)
            return

        # 12. Commit with original submitter as author
        for f in written_files:
            run(["git", "add", f], cwd=project_root)

        type_label = item_type.capitalize()
        commit_msg = (
            f"Add new {type_label}: {item_name} ({item_id})\n\n"
            f"Auto-implemented from issue #{args.issue_number}."
        )

        run([
            "git", "commit",
            "--author", f"{author_name} <{author_email}>",
            "-m", commit_msg,
        ], cwd=project_root)

        # 13. Push and create PR
        print("Pushing branch...", file=sys.stderr)
        run(["git", "push", "-u", "origin", branch_name], cwd=project_root)

        pr_title = f"Add new {type_label}: {item_name} ({item_id})"

        # Build PR body
        pr_lines = []
        pr_lines.append(f"> **This PR was auto-generated** from a new {item_type} "
                        "submission. Please review the files below before merging.")
        pr_lines.append("")
        pr_lines.append("## Summary")
        pr_lines.append("")
        pr_lines.append(f"Adds new {item_type} from #{args.issue_number}.")
        pr_lines.append("")
        pr_lines.append("| Field | Value |")
        pr_lines.append("|---|---|")
        pr_lines.append(f"| Type | {type_label} |")
        pr_lines.append(f"| ID | `{item_id}` |")
        pr_lines.append(f"| Name | {item_name} |")
        if objective_name:
            pr_lines.append(f"| Objective | {objective_name} |")
        pr_lines.append("")

        # Files
        pr_lines.append("## Files")
        pr_lines.append("")
        for f in written_files:
            rel = os.path.relpath(f, project_root)
            pr_lines.append(f"- `{rel}`")
        pr_lines.append("")

        # Warnings
        if all_warnings:
            pr_lines.append("## :warning: Warnings")
            pr_lines.append("")
            for w in all_warnings:
                pr_lines.append(f"- {w}")
            pr_lines.append("")

        # Cross-references
        if cross_refs:
            pr_lines.append("## Manual steps needed")
            pr_lines.append("")
            pr_lines.append("The following cross-references need manual attention:")
            pr_lines.append("")
            for note in cross_refs:
                pr_lines.append(f"- {note}")
            pr_lines.append("")

        # Attribution
        pr_lines.append("## Attribution")
        pr_lines.append("")
        pr_lines.append(f"Original submission by @{issue['user']['login']} "
                        f"in #{args.issue_number}.")
        pr_lines.append(f"Commit authored as: {author_name} <{author_email}>")
        pr_lines.append("")
        pr_lines.append(f"Resolves #{args.issue_number}")

        pr_body = '\n'.join(pr_lines)

        # Write PR body to temp file to avoid command-line length limits
        pr_body_file = os.path.join(project_root, ".pr_body.md")
        with open(pr_body_file, 'w') as f:
            f.write(pr_body)

        try:
            pr_url = run([
                "gh", "pr", "create",
                "--head", branch_name,
                "--title", pr_title,
                "--body-file", pr_body_file,
                "--label", f"content: new {item_type}",
                "--label", "autoimplement",
            ], cwd=project_root)
        finally:
            if os.path.exists(pr_body_file):
                os.remove(pr_body_file)

        print(f"PR created: {pr_url}", file=sys.stderr)

        # 14. Post a comment on the original issue linking to the PR
        link_comment = f"PR created: {pr_url}"
        run(["gh", "issue", "comment", str(args.issue_number), "--body", link_comment])

        print(pr_url)

    except Exception as e:
        if not args.dry_run:
            print(f"Error during implementation: {e}", file=sys.stderr)
            subprocess.run(["git", "checkout", "-"], cwd=project_root,
                           capture_output=True, text=True)
        raise


if __name__ == "__main__":
    main()
