#!/usr/bin/env python3
"""
Migrate SOLVE-IT IDs from old format (T/W/M + digits) to new format (DFT-/DFW-/DFM- + digits).

Usage:
    python admin/migrate_ids.py --dry-run    # Preview changes
    python admin/migrate_ids.py --execute    # Apply changes
"""

import json
import os
import re
import sys


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def convert_id(old_id):
    """Convert an old-format ID to new format.

    T1001 -> DFT-1001, T1002.1 -> DFT-1002.1
    W1001 -> DFW-1001
    M1001 -> DFM-1001
    """
    if re.match(r'^T(\d+(\.\d+)?)$', old_id):
        return 'DFT-' + old_id[1:]
    if re.match(r'^W(\d+)$', old_id):
        return 'DFW-' + old_id[1:]
    if re.match(r'^M(\d+)$', old_id):
        return 'DFM-' + old_id[1:]
    return old_id


def migrate_technique_file(data):
    """Update ID fields inside a technique JSON."""
    changed = False
    if 'id' in data and re.match(r'^T\d+$', data['id']):
        data['id'] = convert_id(data['id'])
        changed = True
    if 'weaknesses' in data:
        new_w = [convert_id(w) for w in data['weaknesses']]
        if new_w != data['weaknesses']:
            data['weaknesses'] = new_w
            changed = True
    if 'subtechniques' in data:
        new_s = [convert_id(s) for s in data['subtechniques']]
        if new_s != data['subtechniques']:
            data['subtechniques'] = new_s
            changed = True
    return changed


def migrate_weakness_file(data):
    """Update ID fields inside a weakness JSON."""
    changed = False
    if 'id' in data and re.match(r'^W\d+$', data['id']):
        data['id'] = convert_id(data['id'])
        changed = True
    if 'mitigations' in data:
        new_m = [convert_id(m) for m in data['mitigations']]
        if new_m != data['mitigations']:
            data['mitigations'] = new_m
            changed = True
    return changed


def migrate_mitigation_file(data):
    """Update ID fields inside a mitigation JSON."""
    changed = False
    if 'id' in data and re.match(r'^M\d+$', data['id']):
        data['id'] = convert_id(data['id'])
        changed = True
    if 'technique' in data and data['technique'] and re.match(r'^T\d+$', data['technique']):
        data['technique'] = convert_id(data['technique'])
        changed = True
    return changed


def migrate_solve_it_json(data):
    """Update technique IDs in solve-it.json objectives."""
    changed = False
    for obj in data:
        if 'techniques' in obj:
            new_t = [convert_id(t) for t in obj['techniques']]
            if new_t != obj['techniques']:
                obj['techniques'] = new_t
                changed = True
    return changed


def migrate_lab_config(data):
    """Update keys and values in lab config JSON files."""
    if isinstance(data, dict):
        new_data = {}
        changed = False
        for key, value in data.items():
            # Convert technique keys like "T1002:Disk imaging"
            new_key = key
            t_match = re.match(r'^(T\d+)(:.*)$', key)
            if t_match:
                new_key = convert_id(t_match.group(1)) + t_match.group(2)
                changed = True

            # Convert weakness keys like "W1006"
            if re.match(r'^W\d+$', key):
                new_key = convert_id(key)
                changed = True

            # Convert mitigation keys like "M1005"
            if re.match(r'^M\d+$', key):
                new_key = convert_id(key)
                changed = True

            new_val, val_changed = migrate_lab_config(value)
            if val_changed:
                changed = True
            new_data[new_key] = new_val
        return new_data, changed
    elif isinstance(data, list):
        new_list = []
        changed = False
        for item in data:
            new_item, item_changed = migrate_lab_config(item)
            if item_changed:
                changed = True
            new_list.append(new_item)
        return new_list, changed
    elif isinstance(data, str):
        new_val = convert_id(data)
        return new_val, new_val != data
    else:
        return data, False


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('--dry-run', '--execute'):
        print("Usage: python admin/migrate_ids.py --dry-run|--execute")
        sys.exit(1)

    dry_run = sys.argv[1] == '--dry-run'
    project_root = get_project_root()

    renames = []       # (old_path, new_path)
    updates = []       # (path, description)
    deletes = []       # paths to delete

    # --- Techniques ---
    tech_dir = os.path.join(project_root, 'data', 'techniques')
    for fname in sorted(os.listdir(tech_dir)):
        if not fname.endswith('.json'):
            continue
        old_path = os.path.join(tech_dir, fname)

        # Delete T1000.json (demo template)
        if fname == 'T1000.json':
            deletes.append(old_path)
            continue

        m = re.match(r'^T(\d+(?:\.\d+)?)\.json$', fname)
        if not m:
            continue

        with open(old_path, 'r') as f:
            data = json.load(f)

        changed = migrate_technique_file(data)

        new_fname = f'DFT-{m.group(1)}.json'
        new_path = os.path.join(tech_dir, new_fname)

        if not dry_run:
            with open(old_path, 'w') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.write('\n')
            os.rename(old_path, new_path)

        renames.append((fname, new_fname))
        if changed:
            updates.append((new_fname, 'updated ID fields'))

    # --- Weaknesses ---
    weak_dir = os.path.join(project_root, 'data', 'weaknesses')
    for fname in sorted(os.listdir(weak_dir)):
        if not fname.endswith('.json'):
            continue
        m = re.match(r'^W(\d+)\.json$', fname)
        if not m:
            continue

        old_path = os.path.join(weak_dir, fname)
        with open(old_path, 'r') as f:
            data = json.load(f)

        changed = migrate_weakness_file(data)

        new_fname = f'DFW-{m.group(1)}.json'
        new_path = os.path.join(weak_dir, new_fname)

        if not dry_run:
            with open(old_path, 'w') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.write('\n')
            os.rename(old_path, new_path)

        renames.append((fname, new_fname))
        if changed:
            updates.append((new_fname, 'updated ID fields'))

    # --- Mitigations ---
    mit_dir = os.path.join(project_root, 'data', 'mitigations')
    for fname in sorted(os.listdir(mit_dir)):
        if not fname.endswith('.json'):
            continue
        m = re.match(r'^M(\d+)\.json$', fname)
        if not m:
            continue

        old_path = os.path.join(mit_dir, fname)
        with open(old_path, 'r') as f:
            data = json.load(f)

        changed = migrate_mitigation_file(data)

        new_fname = f'DFM-{m.group(1)}.json'
        new_path = os.path.join(mit_dir, new_fname)

        if not dry_run:
            with open(old_path, 'w') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.write('\n')
            os.rename(old_path, new_path)

        renames.append((fname, new_fname))
        if changed:
            updates.append((new_fname, 'updated ID fields'))

    # --- solve-it.json ---
    solve_it_path = os.path.join(project_root, 'data', 'solve-it.json')
    with open(solve_it_path, 'r') as f:
        solve_it_data = json.load(f)

    if migrate_solve_it_json(solve_it_data):
        updates.append(('data/solve-it.json', 'updated technique IDs in objectives'))
        if not dry_run:
            with open(solve_it_path, 'w') as f:
                json.dump(solve_it_data, f, indent=4, ensure_ascii=False)
                f.write('\n')

    # --- Lab config examples ---
    lab_dir = os.path.join(project_root, 'lab_config_examples')
    if os.path.exists(lab_dir):
        for fname in sorted(os.listdir(lab_dir)):
            if not fname.endswith('.json'):
                continue
            lab_path = os.path.join(lab_dir, fname)
            with open(lab_path, 'r') as f:
                lab_data = json.load(f)

            new_lab_data, changed = migrate_lab_config(lab_data)
            if changed:
                updates.append((f'lab_config_examples/{fname}', 'updated IDs in keys/values'))
                if not dry_run:
                    with open(lab_path, 'w') as f:
                        json.dump(new_lab_data, f, indent=4, ensure_ascii=False)
                        f.write('\n')

    # --- Delete T1000 ---
    if not dry_run:
        for path in deletes:
            if os.path.exists(path):
                os.remove(path)

    # --- Summary ---
    print(f"\n{'DRY RUN' if dry_run else 'EXECUTED'} — Migration Summary")
    print("=" * 50)
    print(f"Files renamed: {len(renames)}")
    print(f"Files with updated IDs: {len(updates)}")
    print(f"Files deleted: {len(deletes)}")

    if deletes:
        print("\nDeleted:")
        for p in deletes:
            print(f"  {os.path.basename(p)}")

    if dry_run and renames:
        print(f"\nSample renames (first 10):")
        for old, new in renames[:10]:
            print(f"  {old} -> {new}")
        if len(renames) > 10:
            print(f"  ... and {len(renames) - 10} more")

    if updates:
        print(f"\nFiles with internal ID updates (first 10):")
        for path, desc in updates[:10]:
            print(f"  {path}: {desc}")
        if len(updates) > 10:
            print(f"  ... and {len(updates) - 10} more")


if __name__ == '__main__':
    main()
