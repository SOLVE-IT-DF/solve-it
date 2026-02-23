"""
Shared utilities for the update issue parsers.

Provides:
- is_no_response(value) — checks for blank or '_No response_'
- build_change_summary(before, after) — human-readable diff of two JSON dicts
- build_error_comment(item_type, item_id, browse_url) — error comment when ID not found
"""

import json


# Both hyphenated and underscored forms for matching KnowledgeBase output
ASTM_CLASSES = {"INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT",
                "INAC_EX", "INAC_AS", "INAC_ALT", "INAC_COR"}


def is_no_response(value):
    """Return True if the value is blank or the GitHub default '_No response_'."""
    if not value:
        return True
    return value.strip() in ('', '_No response_')


def build_change_summary(before, after):
    """
    Build a human-readable summary of changes between two JSON-serialisable dicts.

    Returns a list of markdown bullet strings describing what changed.
    If nothing changed, returns a single-item list saying so.
    """
    changes = []

    all_keys = list(dict.fromkeys(list(before.keys()) + list(after.keys())))

    for key in all_keys:
        old_val = before.get(key)
        new_val = after.get(key)

        if old_val == new_val:
            continue

        # Both are lists — compute added/removed
        if isinstance(old_val, list) and isinstance(new_val, list):
            old_set = set(old_val)
            new_set = set(new_val)
            added = sorted(new_set - old_set)
            removed = sorted(old_set - new_set)
            parts = []
            if added:
                parts.append("added " + ", ".join(f"'{a}'" for a in added))
            if removed:
                parts.append("removed " + ", ".join(f"'{r}'" for r in removed))
            if parts:
                changes.append(f"- **{key}**: {'; '.join(parts)}")
            continue

        # ASTM flags — show as set/cleared
        if key in ASTM_CLASSES:
            if new_val == "x" and old_val != "x":
                changes.append(f"- **{key}**: set")
            elif new_val != "x" and old_val == "x":
                changes.append(f"- **{key}**: cleared")
            continue

        # Scalar change
        changes.append(f"- **{key}**: changed")

    if not changes:
        return ["No changes detected."]

    return changes


def build_error_comment(item_type, item_id, browse_url):
    """Build a GitHub comment for when the requested item ID is not found."""
    lines = []
    lines.append(f"**Error:** {item_type} `{item_id}` was not found in the knowledge base.")
    lines.append("")
    lines.append(f"Please check the ID and try again. "
                 f"You can browse existing {item_type.lower()}s [here]({browse_url}).")
    lines.append("")
    lines.append("---")
    lines.append("*This comment was automatically generated from the update form.*")
    return '\n'.join(lines)


def build_update_comment(item_type, item_id, item_name, before, after):
    """Build the full BEFORE/AFTER/summary comment for an update proposal."""
    summary_lines = build_change_summary(before, after)

    lines = []
    lines.append(f"## Proposed update to {item_id}: {item_name}")
    lines.append("")
    lines.append("### Current")
    lines.append("```json")
    lines.append(json.dumps(before, indent=4))
    lines.append("```")
    lines.append("")
    lines.append("### Proposed")
    lines.append("```json")
    lines.append(json.dumps(after, indent=4))
    lines.append("```")
    lines.append("")
    lines.append("### Summary of changes")
    lines.extend(summary_lines)
    lines.append("")
    lines.append("---")
    lines.append("*This comment was automatically generated from the update form.*")
    return '\n'.join(lines)
