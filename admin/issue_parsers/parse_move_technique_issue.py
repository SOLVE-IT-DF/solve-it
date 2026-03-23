"""
Parses a GitHub issue created from the 'Move Technique' template
and generates a summary comment describing the proposed move.

Infers the move type from the destination ID prefix:
  - DFO-xxxx → move/promote technique to an objective
  - DFT-xxxx → demote technique to be a subtechnique

Usage:
    python3 admin/parse_move_technique_issue.py --issue-body-file issue_body.md
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body
from update_utils import build_error_comment
from solve_it_library import KnowledgeBase


BROWSE_TECHNIQUES = "https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/techniques"


def find_current_parent(kb, technique_id):
    """Find the parent technique that lists this technique as a subtechnique.

    Returns the parent technique ID, or None if not a subtechnique.
    """
    for t_id in kb.list_techniques():
        t = kb.get_technique(t_id)
        if t and technique_id in t.get('subtechniques', []):
            return t_id
    return None


def find_current_objectives(kb, technique_id):
    """Find all objectives that directly list this technique.

    Returns a list of (objective_id, objective_name) tuples.
    """
    results = []
    for obj in kb.list_objectives():
        if technique_id in obj.get('techniques', []):
            results.append((obj.get('id'), obj.get('name')))
    return results


def build_move_comment(technique_id, technique_name, dest_id, dest_label,
                       move_type, move_description, changes, rationale=None):
    """Build the summary comment for a proposed move."""
    lines = []
    lines.append(f"## Proposed move: {technique_id} ({technique_name})")
    lines.append("")
    lines.append(f"**Move type:** {move_type}")
    lines.append("")
    lines.append(move_description)
    lines.append("")
    if rationale:
        lines.append("### Rationale")
        lines.append("")
        lines.append(rationale)
        lines.append("")
    lines.append("### Changes required")
    lines.append("")
    for change in changes:
        lines.append(f"- {change}")
    lines.append("")
    lines.append("---")
    lines.append("*This comment was automatically generated from the move technique form.*")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse a move technique issue form")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--issue-body', type=str, help="Issue body as a string")
    group.add_argument('--issue-body-file', type=str, help="File containing the issue body")
    parser.add_argument('--output', type=str, help="Output file for the comment (default: stdout)")
    args = parser.parse_args()

    if args.issue_body_file:
        with open(args.issue_body_file) as f:
            body = f.read()
    else:
        body = args.issue_body

    fields = parse_issue_body(body)

    # Validate technique ID
    technique_id = fields.get("Technique to move", "").strip()
    if not re.match(r'^DFT-\d{4,6}$', technique_id):
        print(f"Error: Invalid technique ID format: '{technique_id}'", file=sys.stderr)
        sys.exit(1)

    # Validate destination ID
    dest_id = fields.get("Destination", "").strip()
    if not re.match(r'^(DFT|DFO)-\d{4,6}$', dest_id):
        print(f"Error: Invalid destination ID format: '{dest_id}'. Expected DFT-xxxx or DFO-xxxx.", file=sys.stderr)
        sys.exit(1)

    # Extract rationale
    from update_utils import is_no_response
    rationale_raw = fields.get("Rationale", "").strip()
    rationale = rationale_raw if not is_no_response(rationale_raw) else None

    # Load knowledge base
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    # Validate technique exists
    technique = kb.get_technique(technique_id)
    if technique is None:
        comment = build_error_comment("Technique", technique_id, BROWSE_TECHNIQUES)
        _output(comment, args.output)
        return

    technique_name = technique.get('name', '')

    # Determine current location
    current_parent = find_current_parent(kb, technique_id)
    current_objectives = find_current_objectives(kb, technique_id)

    dest_is_objective = dest_id.startswith('DFO-')

    if dest_is_objective:
        # Moving/promoting to an objective
        dest_obj = None
        for obj in kb.list_objectives():
            if obj.get('id') == dest_id:
                dest_obj = obj
                break

        if dest_obj is None:
            comment = build_error_comment("Objective", dest_id,
                                          "https://github.com/SOLVE-IT-DF/solve-it/blob/main/data/solve-it.json")
            _output(comment, args.output)
            return

        dest_label = f"{dest_id} ({dest_obj.get('name')})"
        changes = []

        if current_parent:
            # Promoting from subtechnique
            parent_technique = kb.get_technique(current_parent)
            parent_name = parent_technique.get('name', '') if parent_technique else ''
            move_type = "Promote subtechnique to top-level technique"
            move_description = (f"Promote `{technique_id}` ({technique_name}) from being a subtechnique of "
                                f"`{current_parent}` ({parent_name}) to a top-level technique under "
                                f"objective `{dest_label}`.")
            changes.append(f"Remove `{technique_id}` from `{current_parent}` ({parent_name}) subtechniques list")
            changes.append(f"Add `{technique_id}` to objective `{dest_label}` techniques list")
        elif current_objectives:
            # Moving between objectives
            from_labels = ', '.join(f"`{oid}` ({oname})" for oid, oname in current_objectives)
            move_type = "Move technique to a different objective"
            move_description = (f"Move `{technique_id}` ({technique_name}) from "
                                f"{from_labels} to objective `{dest_label}`.")
            for obj_id, obj_name in current_objectives:
                if obj_id == dest_id:
                    lines = []
                    lines.append(f"## No move needed")
                    lines.append("")
                    lines.append(f"`{technique_id}` ({technique_name}) is already under objective `{dest_id}` ({obj_name}).")
                    lines.append("")
                    lines.append("---")
                    lines.append("*This comment was automatically generated from the move technique form.*")
                    _output('\n'.join(lines), args.output)
                    return
                changes.append(f"Remove `{technique_id}` from objective `{obj_id}` ({obj_name})")
            changes.append(f"Add `{technique_id}` to objective `{dest_label}` techniques list")
        else:
            # Technique exists but isn't under any objective or parent — just add it
            move_type = "Add technique to objective"
            move_description = f"Add `{technique_id}` ({technique_name}) to objective `{dest_label}`."
            changes.append(f"Add `{technique_id}` to objective `{dest_label}` techniques list")

        comment = build_move_comment(technique_id, technique_name, dest_id, dest_label,
                                     move_type, move_description, changes, rationale)

    else:
        # Demoting to subtechnique of another technique
        dest_technique = kb.get_technique(dest_id)
        if dest_technique is None:
            comment = build_error_comment("Technique", dest_id, BROWSE_TECHNIQUES)
            _output(comment, args.output)
            return

        if dest_id == technique_id:
            lines = []
            lines.append(f"## Error")
            lines.append("")
            lines.append(f"A technique cannot be made a subtechnique of itself.")
            lines.append("")
            lines.append("---")
            lines.append("*This comment was automatically generated from the move technique form.*")
            _output('\n'.join(lines), args.output)
            return

        dest_name = dest_technique.get('name', '')
        dest_label = f"{dest_id} ({dest_name})"
        changes = []

        if current_parent:
            parent_technique = kb.get_technique(current_parent)
            parent_name = parent_technique.get('name', '') if parent_technique else ''
            move_type = "Move subtechnique to a different parent technique"
            move_description = (f"Move `{technique_id}` ({technique_name}) from being a subtechnique of "
                                f"`{current_parent}` ({parent_name}) to a subtechnique of "
                                f"`{dest_label}`.")
            changes.append(f"Remove `{technique_id}` from `{current_parent}` ({parent_name}) subtechniques list")
        elif current_objectives:
            from_labels = ', '.join(f"`{oid}` ({oname})" for oid, oname in current_objectives)
            move_type = "Demote technique to subtechnique"
            move_description = (f"Demote `{technique_id}` ({technique_name}) from a top-level technique "
                                f"under {from_labels} to a subtechnique of `{dest_label}`.")
        else:
            move_type = "Demote technique to subtechnique"
            move_description = (f"Make `{technique_id}` ({technique_name}) a subtechnique of "
                                f"`{dest_label}`.")

        for obj_id, obj_name in current_objectives:
            changes.append(f"Remove `{technique_id}` from objective `{obj_id}` ({obj_name})")

        changes.append(f"Add `{technique_id}` to `{dest_id}` ({dest_name}) subtechniques list")

        comment = build_move_comment(technique_id, technique_name, dest_id, dest_label,
                                     move_type, move_description, changes, rationale)

    _output(comment, args.output)


def _output(comment, output_path):
    """Write comment to file or stdout."""
    if output_path:
        with open(output_path, 'w') as f:
            f.write(comment)
    else:
        print(comment)


if __name__ == '__main__':
    main()
