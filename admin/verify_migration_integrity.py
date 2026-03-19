#!/usr/bin/env python3
"""
Verifies that the weakness category migration preserved all data correctly.

Compares the old format (from git history) against the current format,
checking that every weakness has exactly the same ASTM classifications
in the new `categories` list as it had in the old individual fields.

Usage:
    python3 admin/verify_migration_integrity.py
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solve_it_library.models import ASTM_CLASS_MAPPING

# Reverse mapping: new code -> old field name
REVERSE_MAP = {v: k for k, v in ASTM_CLASS_MAPPING.items()}

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')


def get_old_version(filepath):
    """Get the pre-migration version of a file from git."""
    # Find the last commit before migration (the branch point or parent)
    rel_path = os.path.relpath(filepath, PROJECT_ROOT)
    try:
        result = subprocess.run(
            ["git", "show", "main:" + rel_path],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (json.JSONDecodeError, Exception):
        pass

    # Try HEAD~1, HEAD~2 etc. to find old format
    for ref in ["HEAD~1", "HEAD~2", "HEAD~3", "main~1"]:
        try:
            result = subprocess.run(
                ["git", "show", f"{ref}:{rel_path}"],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Check if this is old format (has INCOMP field)
                if "INCOMP" in data or "INAC-EX" in data:
                    return data
        except (json.JSONDecodeError, Exception):
            continue
    return None


def old_flags_to_set(old_data):
    """Convert old format fields to a set of new-style category codes."""
    categories = set()
    for old_key, new_code in ASTM_CLASS_MAPPING.items():
        # Check both hyphenated and underscored forms
        val = old_data.get(old_key) or old_data.get(old_key.replace("-", "_"))
        if val and str(val).strip().lower() == "x":
            categories.add(new_code)
    return categories


def new_categories_to_set(new_data):
    """Get the set of categories from new format."""
    return set(new_data.get("categories", []))


def main():
    weaknesses_dir = os.path.join(PROJECT_ROOT, "data", "weaknesses")
    files = sorted(f for f in os.listdir(weaknesses_dir) if f.endswith(".json"))

    total = 0
    matched = 0
    mismatched = 0
    skipped = 0
    errors = []

    for filename in files:
        filepath = os.path.join(weaknesses_dir, filename)
        total += 1

        # Load current (new format)
        with open(filepath) as f:
            new_data = json.load(f)

        wid = new_data.get("id", filename)

        # Get old version from git
        old_data = get_old_version(filepath)
        if old_data is None:
            skipped += 1
            continue

        # If old data is already in new format, skip (file was created after migration)
        if "categories" in old_data or "weakness_classes" in old_data:
            skipped += 1
            continue

        old_cats = old_flags_to_set(old_data)
        new_cats = new_categories_to_set(new_data)

        if old_cats == new_cats:
            matched += 1
        else:
            mismatched += 1
            only_old = old_cats - new_cats
            only_new = new_cats - old_cats
            detail = []
            if only_old:
                detail.append(f"lost: {sorted(only_old)}")
            if only_new:
                detail.append(f"gained: {sorted(only_new)}")
            errors.append(f"  {wid}: {', '.join(detail)}")
            errors.append(f"    old fields: {old_cats}")
            errors.append(f"    new categories: {new_cats}")

    print(f"Migration integrity check")
    print(f"  Total files:  {total}")
    print(f"  Matched:      {matched}")
    print(f"  Mismatched:   {mismatched}")
    print(f"  Skipped:      {skipped} (no old version found or already new format)")
    print()

    if errors:
        print("MISMATCHES FOUND:")
        for line in errors:
            print(line)
        sys.exit(1)
    else:
        print("All migrated weaknesses match their original data.")


if __name__ == "__main__":
    main()
