#!/usr/bin/env python3
"""
Compares two TRWM preview comments and summarises what a revision changed.

Preview comments show new items under placeholder IDs (DFW-____-1), which are
numbered by position and so can change between revisions. Each preview also
carries a hidden TRWM_ID_MAP from the Helper's temporary IDs (DFW-temp-0001)
to those placeholders. The temporary IDs stay the same for an item across
revisions, so items are matched on them. Items that already exist in the
knowledge base are matched on their real IDs.

Usage:
    python3 admin/trwm_revision_diff.py --old old_preview.md --new new_preview.md
"""

import argparse
import json
import re


JSON_BLOCK_RE = re.compile(r'```json\s*\n(.*?)\n```', re.DOTALL)
ID_MAP_RE = re.compile(r'<!-- TRWM_ID_MAP: ({.*?}) -->')
REFS_MAP_RE = re.compile(r'<!-- TRWM_REFS_MAP: ({.*?}) -->')
ITEM_PLACEHOLDER_RE = re.compile(r'DF[TWM]-____(?:-\d+)?')
CITE_PLACEHOLDER_RE = re.compile(r'DFCite-____-\d+')

KIND_NAMES = {"DFT": "technique", "DFW": "weakness", "DFM": "mitigation"}


def _hidden_map(regex, body):
    match = regex.search(body)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def preview_items(body):
    """Return {stable_key: item} for every item a preview comment shows.

    stable_key is the temporary ID for a new item and the real ID for an
    existing one. Placeholders inside each item (its own ID, and links to
    other new items or new references) are rewritten to stable values so
    that renumbering between revisions does not show up as a change.
    Where an item appears more than once (an update's BEFORE and AFTER
    blocks), the last block, the proposed version, wins.
    """
    placeholder_to_temp = {v: k for k, v in _hidden_map(ID_MAP_RE, body).items()}
    cite_text = _hidden_map(REFS_MAP_RE, body)

    def stabilise_text(text):
        text = CITE_PLACEHOLDER_RE.sub(
            lambda m: "new reference: " + str(cite_text.get(m.group(0), m.group(0))), text)
        return ITEM_PLACEHOLDER_RE.sub(
            lambda m: placeholder_to_temp.get(m.group(0), m.group(0)), text)

    def stabilise(value):
        # Rewritten after parsing, not in the raw text, because a citation
        # can contain characters that would break the JSON.
        if isinstance(value, str):
            return stabilise_text(value)
        if isinstance(value, list):
            return [stabilise(v) for v in value]
        if isinstance(value, dict):
            return {k: stabilise(v) for k, v in value.items()}
        return value

    items = {}
    for match in JSON_BLOCK_RE.finditer(body):
        try:
            item = stabilise(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            items[item["id"]] = item
    return items


def diff_previews(old_body, new_body):
    """Compare two previews.

    Returns a dict with:
        added:   [(key, name)]
        removed: [(key, name)]
        changed: [(key, name, [field, ...])]
    each sorted by key.
    """
    old = preview_items(old_body)
    new = preview_items(new_body)

    added = [(k, new[k].get("name", "")) for k in sorted(new.keys() - old.keys())]
    removed = [(k, old[k].get("name", "")) for k in sorted(old.keys() - new.keys())]
    changed = []
    for key in sorted(old.keys() & new.keys()):
        fields = sorted(
            f for f in (old[key].keys() | new[key].keys())
            if f != "id" and old[key].get(f) != new[key].get(f)
        )
        if fields:
            changed.append((key, new[key].get("name", ""), fields))
    return {"added": added, "removed": removed, "changed": changed}


def _kind(key):
    return KIND_NAMES.get(key[:3], "item")


def _md(text):
    """Keep submitted names from breaking the markdown list."""
    return str(text).replace("\n", " ").replace("|", "\\|").strip()


def _label(key, name):
    """`kind `ID` (name)`, leaving out the brackets when the item has no name."""
    label = f"{_kind(key)} `{key}`"
    return f"{label} ({_md(name)})" if name and name.strip() else label


def render_summary(diff):
    """Short markdown summary of a diff, for the bot's reply."""
    if not (diff["added"] or diff["removed"] or diff["changed"]):
        return "No changes to the items since the previous revision."
    lines = []
    for key, name in diff["added"]:
        lines.append(f"- **Added** {_label(key, name)}")
    for key, name in diff["removed"]:
        lines.append(f"- **Removed** {_label(key, name)}")
    for key, name, fields in diff["changed"]:
        changed = ", ".join(f"`{f}`" for f in fields)
        lines.append(f"- **Changed** {_label(key, name)}: {changed}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Summarise changes between two TRWM previews")
    parser.add_argument('--old', required=True, help="File holding the earlier preview")
    parser.add_argument('--new', required=True, help="File holding the later preview")
    args = parser.parse_args()
    with open(args.old) as f:
        old = f.read()
    with open(args.new) as f:
        new = f.read()
    print(render_summary(diff_previews(old, new)))


if __name__ == '__main__':
    main()
