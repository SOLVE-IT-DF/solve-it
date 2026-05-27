#!/usr/bin/env python3
"""
Repairs and re-normalises data/solve-it.json after a merge-time formatting
artefact.

The artefact occurs when two autoimplement PRs each append a new last entry
to the same objective's "techniques" list. Each branch produces valid JSON in
isolation (the previous last entry gains a trailing comma, the new entry has
none). When git merges them line-by-line it cannot see that the previous
"last" entry now needs the comma, and produces:

    "DFT-1165",
    "DFT-1186"          <-- missing comma
    "DFT-1187"

This script:
  1. Tries a strict json.load. If it succeeds, re-dumps in canonical form
     and exits 0 (no changes if already canonical).
  2. If the load fails with a missing-comma error, scans for adjacent
     "DF*-NNNN" entries inside an array that lack a separator comma, inserts
     the commas, then re-validates and re-dumps.
  3. Exits non-zero if it cannot make the file parse.

Usage:
    python3 admin/normalise_solve_it_json.py                  # apply in place
    python3 admin/normalise_solve_it_json.py --check          # exit 1 if changes needed, no write
"""

import argparse
import json
import os
import re
import sys


# Adjacent quoted IDs in an array with no comma between them.
# Matches:   "DFT-1186"\n            "DFT-1187"
# Replaces with:  "DFT-1186",\n            "DFT-1187"
MISSING_COMMA_RE = re.compile(
    r'("(?:DFT|DFW|DFM)-\d{4,6}")(\s*\n\s*)(?=")'
)


def attempt_repair(text):
    """Insert missing commas between adjacent quoted IDs. Returns (new_text, n_inserted)."""
    new_text, count = MISSING_COMMA_RE.subn(r'\1,\2', text)
    return new_text, count


def normalise(filepath, check_only=False):
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    repaired_text = original
    repair_note = ""

    try:
        data = json.loads(original)
    except json.JSONDecodeError as exc:
        if "delimiter" not in str(exc):
            print(f"Failed to parse {filepath}: {exc}", file=sys.stderr)
            print("Not a missing-comma error — cannot auto-fix.", file=sys.stderr)
            return 2

        repaired_text, inserted = attempt_repair(original)
        if inserted == 0:
            print(f"Failed to parse {filepath}: {exc}", file=sys.stderr)
            print("No adjacent-ID missing commas found — cannot auto-fix.", file=sys.stderr)
            return 2

        try:
            data = json.loads(repaired_text)
        except json.JSONDecodeError as exc2:
            print(f"Repair attempt did not produce valid JSON: {exc2}", file=sys.stderr)
            return 2

        repair_note = f" (inserted {inserted} missing comma{'s' if inserted != 1 else ''})"

    canonical = json.dumps(data, indent=4) + "\n"

    if canonical == original:
        print(f"{filepath}: already canonical")
        return 0

    if check_only:
        print(f"{filepath}: would change{repair_note}", file=sys.stderr)
        return 1

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(canonical)
    print(f"{filepath}: rewritten{repair_note}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--path", default=None,
        help="Path to solve-it.json (default: data/solve-it.json relative to repo root)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Exit 1 if changes are needed; do not write",
    )
    args = parser.parse_args()

    if args.path:
        filepath = args.path
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(repo_root, "data", "solve-it.json")

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(2)

    sys.exit(normalise(filepath, check_only=args.check))


if __name__ == "__main__":
    main()
