#!/usr/bin/env python3
"""
Migrate SOLVE-IT references from plaintext strings to structured DFCite citations.

Modes:
    --report    Show the mapping table (old text -> new ID) for review
    --execute   Create DFCite-xxxx.json files and rewrite all data files
    --dry-run   Like --execute but don't write any files (default)

Usage:
    python admin/migrate_references.py --report
    python admin/migrate_references.py --dry-run
    python admin/migrate_references.py --execute
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Patterns to skip during migration
TODO_RE = re.compile(r"\btodo\b", re.IGNORECASE)


def collect_references() -> Tuple[Dict[str, List[str]], Set[str]]:
    """Scan all T/W/M files and collect every reference string.

    Returns:
        - ref_to_sources: mapping of stripped reference text -> list of source item IDs
        - todo_refs: set of reference strings matching todo pattern
    """
    ref_to_sources: Dict[str, List[str]] = {}
    todo_refs: Set[str] = set()

    for subdir in ("techniques", "weaknesses", "mitigations"):
        directory = DATA_DIR / subdir
        if not directory.exists():
            continue
        for fp in sorted(directory.glob("*.json")):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            item_id = data.get("id", fp.stem)
            for ref in data.get("references", []):
                # Handle both old string format and already-migrated formats
                if isinstance(ref, str):
                    stripped = ref.strip()
                elif isinstance(ref, list) and len(ref) >= 1:
                    # Already migrated list tuple format — look up plaintext from citation files
                    cite_id = ref[0]
                    txt_path = DATA_DIR / "references" / f"{cite_id}.txt"
                    if txt_path.exists():
                        try:
                            stripped = txt_path.read_text(encoding="utf-8").strip()
                        except Exception:
                            stripped = cite_id
                    else:
                        stripped = cite_id
                elif isinstance(ref, dict) and "DFCite_id" in ref:
                    # Already migrated dict format — look up plaintext
                    cite_id = ref["DFCite_id"]
                    txt_path = DATA_DIR / "references" / f"{cite_id}.txt"
                    if txt_path.exists():
                        try:
                            stripped = txt_path.read_text(encoding="utf-8").strip()
                        except Exception:
                            stripped = cite_id
                    else:
                        stripped = cite_id
                else:
                    continue
                if not stripped:
                    continue
                if TODO_RE.search(stripped):
                    todo_refs.add(stripped)
                    continue
                if stripped not in ref_to_sources:
                    ref_to_sources[stripped] = []
                ref_to_sources[stripped].append(item_id)

    return ref_to_sources, todo_refs


def build_mapping(ref_to_sources: Dict[str, List[str]]) -> OrderedDict:
    """Assign DFCite-1001..DFCite-NNNN sequentially to unique references.

    Returns:
        OrderedDict of plaintext -> DFCite ID, ordered by assigned ID.
    """
    mapping = OrderedDict()
    sorted_refs = sorted(ref_to_sources.keys())
    for i, ref_text in enumerate(sorted_refs, start=1001):
        cite_id = f"DFCite-{i}"
        mapping[ref_text] = cite_id
    return mapping


def find_near_duplicates(refs: List[str], prefix_len: int = 60) -> List[Tuple[str, str]]:
    """Find references that share the same first N characters (possible duplicates)."""
    by_prefix: Dict[str, List[str]] = {}
    for ref in refs:
        prefix = ref[:prefix_len].lower()
        if prefix not in by_prefix:
            by_prefix[prefix] = []
        by_prefix[prefix].append(ref)

    duplicates = []
    for prefix, group in by_prefix.items():
        if len(group) > 1:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    duplicates.append((group[i], group[j]))
    return duplicates


def report_mode(ref_to_sources: Dict[str, List[str]], todo_refs: Set[str]):
    """Print the mapping table and diagnostics for review."""
    mapping = build_mapping(ref_to_sources)

    print(f"Total unique references (excluding todos): {len(mapping)}")
    print(f"Todo entries dropped: {len(todo_refs)}")
    print()

    # URL-only refs
    url_refs = [r for r in mapping if r.startswith("http")]
    academic_refs = [r for r in mapping if not r.startswith("http")]
    print(f"URL-only references: {len(url_refs)}")
    print(f"Academic text references: {len(academic_refs)}")
    print()

    # Mapping table
    print("=" * 80)
    print("REFERENCE MAPPING")
    print("=" * 80)
    for ref_text, cite_id in mapping.items():
        sources = ref_to_sources[ref_text]
        source_str = ", ".join(sources[:5])
        if len(sources) > 5:
            source_str += f" (+{len(sources) - 5} more)"
        print(f"\n{cite_id}:")
        print(f"  Text: {ref_text[:120]}{'...' if len(ref_text) > 120 else ''}")
        print(f"  Used by: {source_str}")

    # Near-duplicate warnings
    near_dupes = find_near_duplicates(list(mapping.keys()))
    if near_dupes:
        print()
        print("=" * 80)
        print("NEAR-DUPLICATE WARNINGS (first 60 chars match)")
        print("=" * 80)
        for a, b in near_dupes:
            print(f"\n  {mapping[a]}: {a[:80]}...")
            print(f"  {mapping[b]}: {b[:80]}...")

    if todo_refs:
        print()
        print("=" * 80)
        print("DROPPED TODO ENTRIES")
        print("=" * 80)
        for t in sorted(todo_refs):
            print(f"  {t}")


def execute_mode(ref_to_sources: Dict[str, List[str]], dry_run: bool = True):
    """Create DFCite files and rewrite data files."""
    mapping = build_mapping(ref_to_sources)
    refs_dir = DATA_DIR / "references"

    # 1. Create DFCite-xxxx.txt files
    if not dry_run:
        refs_dir.mkdir(exist_ok=True)

    created = 0
    for ref_text, cite_id in mapping.items():
        fp = refs_dir / f"{cite_id}.txt"
        if dry_run:
            print(f"  [DRY-RUN] Would create {fp.name}")
        else:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(ref_text + "\n")
            print(f"  Created {fp.name}")
        created += 1

    print(f"\n{'Would create' if dry_run else 'Created'} {created} citation files")

    # 2. Rewrite T/W/M JSON files: replace each reference string with ["DFCite-xxxx", ""]
    rewritten = 0
    for subdir in ("techniques", "weaknesses", "mitigations"):
        directory = DATA_DIR / subdir
        if not directory.exists():
            continue
        for fp in sorted(directory.glob("*.json")):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            old_refs = data.get("references", [])
            if not old_refs:
                # Ensure the field exists as empty list even if not present
                if "references" not in data:
                    data["references"] = []
                continue

            new_refs = []
            for ref in old_refs:
                # Extract the plaintext to look up in mapping
                if isinstance(ref, str):
                    stripped = ref.strip()
                elif isinstance(ref, list) and len(ref) >= 1:
                    # Already-migrated list tuple — resolve via citation file
                    cite_file = DATA_DIR / "references" / f"{ref[0]}.json"
                    if cite_file.exists():
                        try:
                            stripped = json.loads(cite_file.read_text(encoding="utf-8")).get("plaintext", "").strip()
                        except Exception:
                            stripped = ""
                    else:
                        stripped = ""
                elif isinstance(ref, dict) and "DFCite_id" in ref:
                    # Already in dict format — keep as-is
                    new_refs.append(ref)
                    continue
                else:
                    continue
                if not stripped or TODO_RE.search(stripped):
                    continue
                cite_id = mapping.get(stripped)
                if cite_id:
                    new_refs.append({"DFCite_id": cite_id, "relevance_summary_280": ""})
                else:
                    print(f"  WARNING: Unmapped reference in {fp.name}: {stripped[:80]}")

            data["references"] = new_refs
            if dry_run:
                print(f"  [DRY-RUN] Would rewrite {fp.name} ({len(old_refs)} -> {len(new_refs)} refs)")
            else:
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    f.write("\n")
            rewritten += 1

    print(f"\n{'Would rewrite' if dry_run else 'Rewrote'} {rewritten} data files")

    # 3. Add "references": [] to each objective in solve-it.json (if not present)
    objectives_path = DATA_DIR / "solve-it.json"
    try:
        with open(objectives_path, "r", encoding="utf-8") as f:
            objectives = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Could not load solve-it.json: {e}")
        return

    modified = False
    for obj in objectives:
        if "references" not in obj:
            obj["references"] = []
            modified = True

    if modified:
        if dry_run:
            print(f"\n  [DRY-RUN] Would add 'references' field to objectives in solve-it.json")
        else:
            with open(objectives_path, "w", encoding="utf-8") as f:
                json.dump(objectives, f, indent=4, ensure_ascii=False)
                f.write("\n")
            print(f"\n  Added 'references' field to objectives in solve-it.json")
    else:
        print(f"\n  solve-it.json already has 'references' fields on all objectives")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate SOLVE-IT references to structured DFCite citations"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--report", action="store_true", help="Show mapping table for review")
    group.add_argument("--dry-run", action="store_true", help="Simulate execute without writing files")
    group.add_argument("--execute", action="store_true", help="Create citation files and rewrite data")
    args = parser.parse_args()

    ref_to_sources, todo_refs = collect_references()
    print(f"Scanned data files. Found {len(ref_to_sources)} unique references, {len(todo_refs)} todo entries.\n")

    if args.report:
        report_mode(ref_to_sources, todo_refs)
    elif args.dry_run:
        execute_mode(ref_to_sources, dry_run=True)
    elif args.execute:
        execute_mode(ref_to_sources, dry_run=False)


if __name__ == "__main__":
    main()
