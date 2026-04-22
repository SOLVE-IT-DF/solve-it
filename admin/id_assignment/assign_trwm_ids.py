#!/usr/bin/env python3
"""
Assigns IDs to all new items in a TRWM submission issue.

Finds the preview comment (containing "<!-- TRWM_PREVIEW -->"), extracts the
hidden ID map, assigns real IDs for all placeholders in bulk, and posts a
revised comment with the real IDs.

Usage:
    python3 admin/id_assignment/assign_trwm_ids.py --issue-number 42
    python3 admin/id_assignment/assign_trwm_ids.py --issue-number 42 --project-root /path/to/solve-it
"""

import argparse
import json
import os
import re
import subprocess
import sys

# Allow importing IDScanner from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_next_free_ids import IDScanner


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
    """Return the preview comment dict containing the TRWM_PREVIEW marker."""
    for comment in comments:
        body = comment.get("body", "")
        if "<!-- TRWM_PREVIEW -->" in body:
            return comment
    return None


def extract_id_map(comment_body):
    """Extract the placeholder map from the hidden comment.

    The map is embedded as: <!-- TRWM_ID_MAP: {"DFT-temp-0001": "DFT-____", ...} -->
    """
    match = re.search(r'<!-- TRWM_ID_MAP: ({.*?}) -->', comment_body)
    if not match:
        return None
    return json.loads(match.group(1))


def extract_refs_map(comment_body):
    """Extract the DFCite placeholder → BibTeX map from the preview comment.

    The map is embedded as: <!-- TRWM_REFS_MAP: {"DFCite-____-1": "@article{...}", ...} -->
    Returns {} if not present.
    """
    match = re.search(r'<!-- TRWM_REFS_MAP: ({.*?}) -->', comment_body, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def count_needed_ids(id_map, refs_map=None):
    """Count how many IDs are needed per type from the placeholder maps.

    Returns: {"technique": count, "weakness": count, "mitigation": count, "citation": count}
    """
    counts = {"technique": 0, "weakness": 0, "mitigation": 0, "citation": 0}
    for placeholder in id_map.values():
        if placeholder.startswith("DFT-"):
            counts["technique"] += 1
        elif placeholder.startswith("DFW-"):
            counts["weakness"] += 1
        elif placeholder.startswith("DFM-"):
            counts["mitigation"] += 1
    if refs_map:
        counts["citation"] = len(refs_map)
    return counts


def build_replacement_map(id_map, scanner, refs_map=None):
    """Build a map from placeholders to real IDs.

    Args:
        id_map: {temp_id: placeholder} from the preview comment
        scanner: IDScanner instance with scanned IDs
        refs_map: optional {DFCite-____-N: bibtex_text} from the preview comment

    Returns:
        {placeholder: real_id} covering techniques, weaknesses, mitigations,
        and (when refs_map is given) DFCites.
    """
    counts = count_needed_ids(id_map, refs_map)
    replacement_map = {}

    # Get next available IDs for each type
    if counts["technique"] > 0:
        next_technique_ids = scanner.find_next_available(
            scanner.technique_ids, scanner.reserved_technique_ids,
            count=counts["technique"],
        )
    else:
        next_technique_ids = []

    if counts["weakness"] > 0:
        next_weakness_ids = scanner.find_next_available(
            scanner.weakness_ids, scanner.reserved_weakness_ids,
            count=counts["weakness"],
        )
    else:
        next_weakness_ids = []

    if counts["mitigation"] > 0:
        next_mitigation_ids = scanner.find_next_available(
            scanner.mitigation_ids, scanner.reserved_mitigation_ids,
            count=counts["mitigation"],
        )
    else:
        next_mitigation_ids = []

    if counts["citation"] > 0:
        next_citation_ids = scanner.find_next_available(
            scanner.citation_ids, scanner.reserved_citation_ids,
            count=counts["citation"],
        )
    else:
        next_citation_ids = []

    # Assign IDs to placeholders in order
    t_idx, w_idx, m_idx = 0, 0, 0

    # Sort by placeholder to ensure deterministic assignment
    for temp_id, placeholder in sorted(id_map.items(), key=lambda x: x[1]):
        if placeholder.startswith("DFT-"):
            real_id = f"DFT-{next_technique_ids[t_idx]}"
            t_idx += 1
        elif placeholder.startswith("DFW-"):
            real_id = f"DFW-{next_weakness_ids[w_idx]}"
            w_idx += 1
        elif placeholder.startswith("DFM-"):
            real_id = f"DFM-{next_mitigation_ids[m_idx]}"
            m_idx += 1
        else:
            continue
        replacement_map[placeholder] = real_id

    # DFCite placeholders — sort by numeric suffix for stable assignment
    if refs_map:
        def _dfcite_idx(p):
            m = re.search(r'-(\d+)$', p)
            return int(m.group(1)) if m else 0
        for c_idx, placeholder in enumerate(sorted(refs_map.keys(), key=_dfcite_idx)):
            replacement_map[placeholder] = f"DFCite-{next_citation_ids[c_idx]}"

    return replacement_map


def apply_replacements(body, replacement_map):
    """Apply all placeholder-to-real-ID replacements in the comment body.

    Replaces longer placeholders first to avoid partial matches
    (e.g. "DFW-____-10" before "DFW-____-1").
    """
    # Sort by placeholder length descending to avoid partial matches
    for placeholder, real_id in sorted(replacement_map.items(),
                                        key=lambda x: len(x[0]),
                                        reverse=True):
        body = body.replace(placeholder, real_id)
    return body


def post_comment(issue_number, body):
    """Post a new comment on an issue."""
    subprocess.run(
        ["gh", "issue", "comment", str(issue_number), "--body", body],
        text=True, check=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Assign IDs to all new items in a TRWM submission issue",
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

    # 1. Scan for existing and reserved IDs
    scanner = IDScanner(args.project_root)
    scanner.scan_local_files()
    scanner.scan_github_issues_prs()

    # 2. Fetch issue comments and locate the preview comment
    comments = get_issue_comments(args.issue_number)
    preview = find_preview_comment(comments)

    if preview is None:
        print("Error: could not find a TRWM preview comment (<!-- TRWM_PREVIEW --> marker).",
              file=sys.stderr)
        sys.exit(1)

    # 3. Extract the ID map from the preview comment
    id_map = extract_id_map(preview["body"])
    if id_map is None:
        print("Error: could not find TRWM_ID_MAP in preview comment.",
              file=sys.stderr)
        sys.exit(1)

    refs_map = extract_refs_map(preview["body"])

    if not id_map and not refs_map:
        print("No new items to assign IDs to.", file=sys.stderr)
        # Post informational comment so reviewer knows to proceed
        info_comment = (
            "### No new IDs needed\n\n"
            "All items in this submission match existing KB entries. "
            "No ID assignment is required.\n\n"
            "Add the `autoimplement` label to create a PR with the updates."
        )
        post_comment(args.issue_number, info_comment)
        sys.exit(0)

    # 4. Build replacement map (placeholder -> real ID)
    replacement_map = build_replacement_map(id_map, scanner, refs_map=refs_map)
    print(f"Replacement map: {replacement_map}", file=sys.stderr)

    # 5. Apply replacements to the preview comment
    old_body = preview["body"]
    revised_body = apply_replacements(old_body, replacement_map)

    # Also rewrite the TRWM_REFS_MAP so its keys are the real DFCite IDs,
    # making it usable by the autoimplement step to write .bib files.
    if refs_map:
        resolved_refs_map = {
            replacement_map[placeholder]: text
            for placeholder, text in refs_map.items()
            if placeholder in replacement_map
        }
        # Replace the TRWM_REFS_MAP block with one keyed on real DFCite IDs
        revised_body = re.sub(
            r'<!-- TRWM_REFS_MAP: ({.*?}) -->',
            f'<!-- TRWM_REFS_MAP: {json.dumps(resolved_refs_map)} -->',
            revised_body,
            count=1,
            flags=re.DOTALL,
        )

    # Update header text
    revised_body = revised_body.replace(
        "Thanks for your TRWM submission! Here's a preview of the proposed changes:",
        "Your TRWM submission has been assigned IDs. Here are the updated JSON blocks:",
    )
    revised_body = revised_body.replace(
        "IDs with `____` placeholders will be assigned during review "
        "when the `assigned ID` label is added.",
        "All IDs have been assigned. The JSON blocks above are ready to be committed to the knowledge base.",
    )

    if revised_body == old_body:
        print("Error: replacement produced no changes — are IDs already assigned?",
              file=sys.stderr)
        sys.exit(1)

    # 6. Post confirmation comment and revised JSON
    confirmation_lines = ["### Assigned IDs", ""]
    for placeholder, real_id in sorted(replacement_map.items()):
        confirmation_lines.append(f"- `{placeholder}` → **{real_id}**")
    confirmation = '\n'.join(confirmation_lines)

    print("Posting confirmation and revised JSON...", file=sys.stderr)
    post_comment(args.issue_number, confirmation)
    post_comment(args.issue_number, revised_body)

    # 7. Print summary to stdout
    print(json.dumps(replacement_map, indent=2))


if __name__ == "__main__":
    main()
