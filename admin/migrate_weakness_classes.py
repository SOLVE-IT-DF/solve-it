#!/usr/bin/env python3
"""
One-time migration script: converts weakness JSON files from individual ASTM
flag fields to a single `categories` list.

Before:
    {"INCOMP": "x", "INAC-EX": "", ...}

After:
    {"categories": ["ASTM_INCOMP"]}

Idempotent: skips files that already have `categories`.

Usage:
    python3 admin/migrate_categories.py [--dry-run]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solve_it_library.models import ASTM_CLASS_MAPPING

# Old field names (both hyphenated JSON form and underscored Pydantic form)
OLD_FIELDS_HYPHEN = {"INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT"}
OLD_FIELDS_UNDERSCORE = {"INCOMP", "INAC_EX", "INAC_AS", "INAC_ALT", "INAC_COR", "MISINT"}
ALL_OLD_FIELDS = OLD_FIELDS_HYPHEN | OLD_FIELDS_UNDERSCORE

# Desired key order in the output JSON
KEY_ORDER = ["id", "name", "description", "categories", "mitigations", "references"]


def migrate_file(filepath, dry_run=False):
    """Migrate a single weakness JSON file. Returns (migrated, skipped, error) status."""
    with open(filepath) as f:
        data = json.load(f)

    # Idempotent: skip if already migrated
    if "categories" in data:
        return "skipped"

    # Build categories list from old fields
    categories = []
    for old_key, new_code in ASTM_CLASS_MAPPING.items():
        # Check both hyphenated and underscored forms
        val = data.get(old_key) or data.get(old_key.replace("-", "_"))
        if val and val.strip().lower() == "x":
            categories.append(new_code)

    # Remove old fields
    for key in list(data.keys()):
        if key in ALL_OLD_FIELDS:
            del data[key]

    # Insert categories
    data["categories"] = categories

    # Reorder keys to desired order
    ordered = {}
    for key in KEY_ORDER:
        if key in data:
            ordered[key] = data[key]
    # Add any remaining keys not in KEY_ORDER
    for key in data:
        if key not in ordered:
            ordered[key] = data[key]

    if not dry_run:
        with open(filepath, 'w') as f:
            json.dump(ordered, f, indent=4)
            f.write('\n')

    return "migrated"


def main():
    parser = argparse.ArgumentParser(description="Migrate weakness files to categories format")
    parser.add_argument('--dry-run', action='store_true', help="Show what would happen without writing files")
    args = parser.parse_args()

    weaknesses_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'weaknesses')

    if not os.path.isdir(weaknesses_dir):
        print(f"Error: {weaknesses_dir} not found", file=sys.stderr)
        sys.exit(1)

    files = sorted(f for f in os.listdir(weaknesses_dir) if f.endswith('.json'))
    migrated = 0
    skipped = 0
    errors = 0

    for filename in files:
        filepath = os.path.join(weaknesses_dir, filename)
        try:
            status = migrate_file(filepath, args.dry_run)
            if status == "migrated":
                migrated += 1
                if args.dry_run:
                    print(f"  [DRY RUN] Would migrate: {filename}")
                else:
                    print(f"  Migrated: {filename}")
            else:
                skipped += 1
                print(f"  Skipped (already migrated): {filename}")
        except Exception as e:
            errors += 1
            print(f"  ERROR: {filename}: {e}", file=sys.stderr)

    print(f"\nSummary: {migrated} migrated, {skipped} skipped, {errors} errors")
    if args.dry_run:
        print("(Dry run — no files were modified)")


if __name__ == '__main__':
    main()
