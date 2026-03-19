#!/usr/bin/env python3
"""Generate a changelog for the SOLVE-IT knowledge base from git history.

Two-strategy approach:
  A) Regex on structured commit messages (autoimplement, TRWM, references)
  B) File-based detection via git diff-tree for older/freeform commits

Outputs:
  - changelog/changelog.jsonl  (machine-readable, one JSON object per line)
  - changelog/CHANGELOG_DATA.md  (human-readable, grouped by month)
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

OLD_ID_MAP = {"T": "DFT", "W": "DFW", "M": "DFM"}
OLD_ID_RE = re.compile(r"^([TWM])(\d{4,6})$")
NEW_ID_RE = re.compile(r"^(DFT|DFW|DFM)-\d{4,6}$")
CITE_ID_RE = re.compile(r"^DFCite-\d{4,6}$")


def normalize_id(raw_id: str) -> str:
    """Convert old-style T1001 to DFT-1001; pass through new-style IDs."""
    m = OLD_ID_RE.match(raw_id)
    if m:
        return f"{OLD_ID_MAP[m.group(1)]}-{m.group(2)}"
    return raw_id


def id_to_type(item_id: str) -> str | None:
    """Map a KB ID (old or new format) to its type string."""
    if item_id.startswith(("DFT-", "T")):
        return "technique"
    if item_id.startswith(("DFW-", "W")):
        return "weakness"
    if item_id.startswith(("DFM-", "M")):
        return "mitigation"
    if item_id.startswith("DFCite-"):
        return "reference"
    return None


# ---------------------------------------------------------------------------
# Data-file path helpers
# ---------------------------------------------------------------------------

# Maps relative paths under data/ to type
DATA_DIR_TYPE = {
    "data/techniques": "technique",
    "data/weaknesses": "weakness",
    "data/mitigations": "mitigation",
    "data/references": "reference",
}

SKIP_FILES = {"data/solve-it.json"}

# Filename → ID patterns (new and old formats)
FILE_ID_RE = re.compile(r"(DFT-\d+|DFW-\d+|DFM-\d+|DFCite-\d+)")
OLD_FILE_ID_RE = re.compile(r"^([TWM])(\d{4,6})$")


def classify_data_file(path: str) -> tuple[str | None, str | None]:
    """Return (type, raw_id) for a data file path, or (None, None) if not a KB item.

    The raw_id preserves the original format (e.g. T1001 or DFT-1001).
    """
    if path in SKIP_FILES:
        return None, None
    for prefix, item_type in DATA_DIR_TYPE.items():
        if path.startswith(prefix + "/"):
            stem = Path(path).stem
            # Try new-style IDs first (DFT-1001)
            m = FILE_ID_RE.search(stem)
            if m:
                return item_type, m.group(1)
            # Try old-style IDs (T1001) — preserve original format
            m = OLD_FILE_ID_RE.match(stem)
            if m:
                return item_type, stem  # e.g. "T1001"
            return item_type, None
    return None, None


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"git error: {result.stderr.strip()}", file=sys.stderr)
    return result.stdout


def get_repo_commit_url() -> str | None:
    """Derive the GitHub commit URL base from the git remote."""
    raw = git(["remote", "get-url", "origin"])
    url = raw.strip()
    if not url:
        return None
    # Normalise ssh and https URLs to https base
    url = re.sub(r"\.git$", "", url)
    url = re.sub(r"^git@github\.com:", "https://github.com/", url)
    return url + "/commit/"


def get_commits(since: str | None = None, after_sha: str | None = None) -> list[dict]:
    """Return list of {sha, date, subject, body} dicts, oldest first."""
    log_args = [
        "log",
        "--no-merges",
        "--format=%H%x00%aI%x00%s%x00%b%x1e",
        "--reverse",
    ]
    if since:
        log_args.append(f"--since={since}")
    if after_sha:
        log_args.append(f"{after_sha}..HEAD")

    raw = git(log_args)
    commits = []
    for block in raw.split("\x1e"):
        block = block.strip()
        if not block:
            continue
        parts = block.split("\x00", 3)
        if len(parts) < 4:
            continue
        commits.append({
            "sha": parts[0],
            "date": parts[1][:10],  # ISO date only
            "subject": parts[2],
            "body": parts[3].strip(),
        })
    return commits


def get_diff_tree(sha: str) -> list[tuple[str, str, str | None]]:
    """Return [(status, path, old_path), ...] for changed files in a commit.

    Uses -M for rename detection. For renames, status is 'R', path is the
    new path, and old_path is the original path. For other statuses old_path
    is None.
    """
    raw = git(["diff-tree", "--no-commit-id", "-r", "--name-status", "-M", sha])
    result = []
    for line in raw.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0][0]  # first char (strips rename similarity %)
        if status == "R" and len(parts) == 3:
            # Rename: status\told_path\tnew_path
            result.append(("R", parts[2], parts[1]))
        elif len(parts) >= 2:
            result.append((status, parts[1], None))
    return result


def read_file_at_commit(sha: str, path: str) -> str | None:
    """Read file contents at a specific commit."""
    result = subprocess.run(
        ["git", "show", f"{sha}:{path}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def extract_name_from_json(sha: str, path: str) -> str | None:
    """Read the 'name' field from a JSON file at a given commit."""
    content = read_file_at_commit(sha, path)
    if not content:
        return None
    try:
        data = json.loads(content)
        return data.get("name")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# Strategy A: Regex on commit messages
# ---------------------------------------------------------------------------

# Add new Technique: <name> (<ID>)
RE_ADD_NEW = re.compile(
    r"^Add new (Technique|Weakness|Mitigation):\s+(.+?)\s+\(([A-Z]+-?\d+)\)$"
)

# Add/Update TRWM submission: <name> (<ID>)
RE_TRWM = re.compile(
    r"^(Add|Update) TRWM submission:\s+(.+?)\s+\(([A-Z]+-?\d+)\)$"
)

# Add new reference: <ID>
RE_ADD_REF = re.compile(r"^Add new reference:\s+(DFCite-\d+)$")

# Update DFCite relevance: <ID> in <ID>
RE_UPDATE_REF = re.compile(
    r"^Update DFCite relevance:\s+(DFCite-\d+)\s+in\s+([A-Z]+-?\d+)$"
)

ISSUE_RE = re.compile(r"issue\s+#(\d+)", re.IGNORECASE)


def extract_issue(body: str) -> int | None:
    m = ISSUE_RE.search(body)
    return int(m.group(1)) if m else None


def strategy_a(commit: dict) -> list[dict]:
    """Parse structured commit messages into changelog entries."""
    subj = commit["subject"]
    short_sha = commit["sha"][:7]
    issue = extract_issue(commit["body"])
    entries = []

    m = RE_ADD_NEW.match(subj)
    if m:
        item_type = m.group(1).lower()
        name = m.group(2)
        item_id = normalize_id(m.group(3))
        entries.append({
            "date": commit["date"],
            "action": "added",
            "type": item_type,
            "id": item_id,
            "name": name,
            "commit": short_sha,
            "source": "autoimplement",
            "issue": issue,
        })
        return entries

    m = RE_TRWM.match(subj)
    if m:
        verb = m.group(1)
        name = m.group(2)
        item_id = normalize_id(m.group(3))
        action = "added" if verb == "Add" else "updated"
        entries.append({
            "date": commit["date"],
            "action": action,
            "type": id_to_type(item_id) or "technique",
            "id": item_id,
            "name": name,
            "commit": short_sha,
            "source": "trwm",
            "issue": issue,
        })
        return entries

    m = RE_ADD_REF.match(subj)
    if m:
        entries.append({
            "date": commit["date"],
            "action": "added",
            "type": "reference",
            "id": m.group(1),
            "name": m.group(1),
            "commit": short_sha,
            "source": "autoimplement",
            "issue": issue,
        })
        return entries

    m = RE_UPDATE_REF.match(subj)
    if m:
        entries.append({
            "date": commit["date"],
            "action": "updated",
            "type": "reference",
            "id": m.group(1),
            "name": f"{m.group(1)} in {m.group(2)}",
            "commit": short_sha,
            "source": "autoimplement",
            "issue": issue,
        })
        return entries

    return entries


# ---------------------------------------------------------------------------
# Strategy B: File-based detection
# ---------------------------------------------------------------------------

BULK_THRESHOLD = 50


def strategy_b(commit: dict) -> list[dict]:
    """Detect KB changes from file diffs for commits not caught by Strategy A."""
    changes = get_diff_tree(commit["sha"])
    data_changes = []
    for status, path, old_path in changes:
        if status == "R":
            # Rename: check if this is an ID migration (T1001.json → DFT-1001.json)
            old_type, old_id = classify_data_file(old_path)
            new_type, new_id = classify_data_file(path)
            if old_type and new_type and old_id and new_id:
                # Same item renamed — treat as update, use the new path for reading
                data_changes.append(("R", path, new_type, new_id, old_path))
            continue
        item_type, item_id = classify_data_file(path)
        if item_type and item_id:
            data_changes.append((status, path, item_type, item_id, None))

    if not data_changes:
        return []

    # Summarise bulk commits as a single entry
    if len(data_changes) > BULK_THRESHOLD:
        short_sha = commit["sha"][:7]
        # Count by status
        counts = defaultdict(int)
        for status, *_ in data_changes:
            counts[status] += 1
        parts = []
        if counts.get("R"):
            parts.append(f"{counts['R']} renamed")
        if counts.get("A"):
            parts.append(f"{counts['A']} added")
        if counts.get("M"):
            parts.append(f"{counts['M']} updated")
        if counts.get("D"):
            parts.append(f"{counts['D']} deleted")
        summary = ", ".join(parts)
        return [{
            "date": commit["date"],
            "action": "bulk",
            "type": "bulk",
            "id": "N/A",
            "name": f"Bulk change: {summary} items",
            "commit": short_sha,
            "source": "manual",
            "issue": None,
        }]

    short_sha = commit["sha"][:7]
    issue = extract_issue(commit["body"]) or extract_issue(commit["subject"])
    entries = []

    for status, path, item_type, item_id, old_path in data_changes:
        if status == "A":
            action = "added"
        elif status == "D":
            action = "deleted"
        elif status == "R":
            action = "updated"
        else:
            action = "updated"

        # Try to get the name from the file
        name = None
        if path.endswith(".json"):
            if status == "D":
                # File was deleted — read from parent commit
                name = extract_name_from_json(commit["sha"] + "~1", path)
            else:
                name = extract_name_from_json(commit["sha"], path)
        if not name:
            name = item_id

        # Determine source
        body_lower = (commit["subject"] + " " + commit["body"]).lower()
        if "auto-implemented" in body_lower or "autoimplement" in body_lower:
            source = "autoimplement"
        elif "trwm" in body_lower:
            source = "trwm"
        else:
            source = "manual"

        entries.append({
            "date": commit["date"],
            "action": action,
            "type": item_type,
            "id": item_id,
            "name": name,
            "commit": short_sha,
            "source": source,
            "issue": issue,
        })

    return entries


# ---------------------------------------------------------------------------
# Deduplication and merging
# ---------------------------------------------------------------------------


def deduplicate(a_entries: list[dict], b_entries: list[dict]) -> list[dict]:
    """Merge Strategy A and B results; A takes priority on conflicts."""
    seen = set()
    result = []

    for entry in a_entries:
        key = (entry["commit"], entry["id"])
        seen.add(key)
        result.append(entry)

    for entry in b_entries:
        key = (entry["commit"], entry["id"])
        if key not in seen:
            seen.add(key)
            result.append(entry)

    return result


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict]:
    entries = []
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    return entries


def write_jsonl(entries: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_markdown(entries: list[dict], path: Path) -> None:
    """Generate CHANGELOG.md grouped by month, newest first."""
    # Group by year-month
    by_month: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        month_key = entry["date"][:7]  # YYYY-MM
        by_month[month_key].append(entry)

    months_sorted = sorted(by_month.keys(), reverse=True)

    month_names = {
        "01": "January", "02": "February", "03": "March",
        "04": "April", "05": "May", "06": "June",
        "07": "July", "08": "August", "09": "September",
        "10": "October", "11": "November", "12": "December",
    }

    lines = ["# SOLVE-IT Knowledge Base Changelog", ""]

    for month_key in months_sorted:
        year, mm = month_key.split("-")
        month_name = month_names.get(mm, mm)
        lines.append(f"## {month_name} {year}")
        lines.append("")

        # Sort entries within month by date descending, then by id
        month_entries = sorted(
            by_month[month_key],
            key=lambda e: (e["date"], e["id"]),
            reverse=True,
        )

        for entry in month_entries:
            # Bulk entries get their own format
            # Commit link
            commit_sha = entry.get("commit", "")
            commit_url = entry.get("commit_url")
            commit_link = f" [`{commit_sha}`]({commit_url})" if commit_url else ""

            if entry["action"] == "bulk":
                lines.append(
                    f"- **{entry['date']}** {entry['name']}{commit_link}"
                )
                continue

            if entry["action"] == "added":
                action = "Added"
            elif entry["action"] == "updated":
                action = "Updated"
            elif entry["action"] == "deleted":
                action = "Deleted"
            else:
                action = entry["action"].capitalize()

            item_type = entry["type"]
            source_tag = f" ({entry['source'].upper()})" if entry["source"] != "manual" else ""

            # For references with "DFCite-XXXX in DFT-XXXX" style names, use as-is
            name_part = entry["name"]
            if name_part == entry["id"]:
                # No separate name, just show the ID
                lines.append(
                    f"- **{entry['date']}** {action} {item_type}{source_tag}: {entry['id']}{commit_link}"
                )
            else:
                lines.append(
                    f"- **{entry['date']}** {action} {item_type}{source_tag}: {name_part} ({entry['id']}){commit_link}"
                )

        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate a changelog for the SOLVE-IT knowledge base from git history."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Path to the project root (default: auto-detect)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for JSONL (default: changelog/changelog.jsonl)",
    )
    parser.add_argument(
        "--render-markdown",
        type=Path,
        default=None,
        help="Output path for CHANGELOG.md (default: changelog/CHANGELOG_DATA.md)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Incremental mode: only process commits since last changelog entry",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only process commits since this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print entries without writing files",
    )
    args = parser.parse_args()

    global PROJECT_ROOT
    PROJECT_ROOT = (args.project_root or PROJECT_ROOT).resolve()

    output_path = args.output or (PROJECT_ROOT / "changelog" / "changelog.jsonl")
    md_path = args.render_markdown or (PROJECT_ROOT / "changelog" / "CHANGELOG_DATA.md")

    # Determine commit range
    existing_entries = []
    after_sha = None

    if args.append and output_path.exists():
        existing_entries = read_jsonl(output_path)
        if existing_entries:
            # Collect all unique commit SHAs from existing entries
            all_shas = list({e["commit"] for e in existing_entries if e.get("commit")})
            if all_shas:
                # Use git log to find which known SHA appears most recently
                # by walking history and returning the first match
                log_output = git(["log", "--no-merges", "--format=%H", "--reverse"])
                all_commits = log_output.strip().splitlines()
                # Build lookup of short SHA -> full SHA
                latest_full = None
                for full in all_commits:
                    if full[:7] in all_shas:
                        latest_full = full  # keep updating; last match = most recent
                if latest_full:
                    after_sha = latest_full
                    print(f"Appending: processing commits after {latest_full[:7]}...")
                else:
                    print(
                        "Warning: could not resolve any existing SHAs, processing all commits.",
                        file=sys.stderr,
                    )

    commits = get_commits(since=args.since, after_sha=after_sha)
    print(f"Processing {len(commits)} commits...")

    all_a = []
    all_b = []

    for i, commit in enumerate(commits):
        a_entries = strategy_a(commit)
        if a_entries:
            all_a.extend(a_entries)
        else:
            b_entries = strategy_b(commit)
            all_b.extend(b_entries)

        if (i + 1) % 100 == 0:
            print(f"  ...processed {i + 1}/{len(commits)} commits")

    new_entries = deduplicate(all_a, all_b)

    # Add commit URL to new entries
    commit_base_url = get_repo_commit_url()
    if commit_base_url:
        for entry in new_entries:
            entry["commit_url"] = commit_base_url + entry["commit"]

    print(
        f"Found {len(new_entries)} new entries "
        f"(Strategy A: {len(all_a)}, Strategy B: {len(all_b)})"
    )

    if args.dry_run:
        for entry in new_entries:
            print(json.dumps(entry, ensure_ascii=False))
        return

    # Combine with existing entries and sort chronologically
    all_entries = existing_entries + new_entries
    all_entries.sort(key=lambda e: (e["date"], e["id"]))

    # Backfill commit_url for any existing entries missing it
    if commit_base_url:
        for entry in all_entries:
            if "commit_url" not in entry and entry.get("commit"):
                entry["commit_url"] = commit_base_url + entry["commit"]

    # Write outputs
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(all_entries, output_path)
    print(f"Wrote {len(all_entries)} entries to {output_path}")

    render_markdown(all_entries, md_path)
    print(f"Rendered CHANGELOG.md to {md_path}")


if __name__ == "__main__":
    main()
