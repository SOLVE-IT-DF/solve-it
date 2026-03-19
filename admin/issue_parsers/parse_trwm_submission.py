"""
Parses a GitHub issue created from the 'TRWM Submission' form template
and generates a preview comment with individual KB-compatible JSON blocks.

The TRWM SOLVE-IT Helper app exports a single JSON containing a technique
with all its weaknesses and mitigations. This script:
1. Extracts and validates the JSON from the issue body
2. Classifies items as new (temp ID) or existing (real ID)
3. Verifies existing references against the KB
4. Generates indexed placeholders for new items
5. Builds a markdown comment with summary, JSON blocks, and hidden ID map

Usage:
    python3 admin/issue_parsers/parse_trwm_submission.py \
        --project-root . --issue-body-file issue_body.md --output comment.md
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from parse_technique_issue import parse_issue_body
from solve_it_library import KnowledgeBase
from update_utils import build_change_summary


# Regex patterns for temp vs real IDs
TEMP_ID_RE = re.compile(r'^(DFT|DFW|DFM)-temp-\d+$')
REAL_TECHNIQUE_RE = re.compile(r'^DFT-\d{4,6}$')
REAL_WEAKNESS_RE = re.compile(r'^DFW-\d{4,6}$')
REAL_MITIGATION_RE = re.compile(r'^DFM-\d{4,6}$')

# Full KB schemas with all fields (empty defaults)
TECHNIQUE_FIELDS = [
    "id", "name", "description", "synonyms", "details",
    "subtechniques", "examples", "weaknesses",
    "CASE_input_classes", "CASE_output_classes", "references",
]

WEAKNESS_FIELDS = [
    "id", "name", "categories", "mitigations", "references",
]

MITIGATION_FIELDS = [
    "id", "name", "references",
]

# Default values by type
FIELD_DEFAULTS = {
    str: "",
    list: [],
}


def is_temp_id(item_id):
    """Check if an ID is a temp ID from the TRWM Helper."""
    return bool(TEMP_ID_RE.match(item_id))


def extract_json_from_field(text):
    """Extract JSON from a form field, stripping any code fences."""
    text = text.strip()
    # Remove code fences if present
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove first line (```json or ```) and last line (```)
        if lines[-1].strip() == '```':
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = '\n'.join(lines)
    return text


def normalize_to_kb_schema(item, field_list):
    """Normalize an item to the full KB schema, including all fields."""
    normalized = {}
    for field in field_list:
        if field in item:
            normalized[field] = item[field]
        else:
            # Determine default based on what other items typically have
            if field in ("synonyms", "subtechniques", "examples", "weaknesses",
                         "CASE_input_classes", "CASE_output_classes",
                         "mitigations", "references"):
                normalized[field] = []
            else:
                normalized[field] = ""
    return normalized


def build_placeholder_map(trwm_data):
    """Build a mapping from temp IDs to indexed placeholders.

    Returns:
        (placeholder_map, new_items, existing_items)
        - placeholder_map: {temp_id: placeholder} e.g. {"DFT-temp-0001": "DFT-____"}
        - new_items: {"techniques": [...], "weaknesses": [...], "mitigations": [...]}
        - existing_items: {"techniques": [...], "weaknesses": [...], "mitigations": [...]}
    """
    placeholder_map = {}
    new_items = {"techniques": [], "weaknesses": [], "mitigations": []}
    existing_items = {"techniques": [], "weaknesses": [], "mitigations": []}

    # Process techniques
    technique_idx = 0
    for tid, technique in trwm_data.get("techniques", {}).items():
        if is_temp_id(tid):
            # For a single technique, no index suffix needed
            technique_idx += 1
            if technique_idx == 1 and len(trwm_data.get("techniques", {})) == 1:
                placeholder = "DFT-____"
            else:
                placeholder = f"DFT-____-{technique_idx}"
            placeholder_map[tid] = placeholder
            new_items["techniques"].append(technique)
        else:
            existing_items["techniques"].append(technique)

    # Process weaknesses
    weakness_idx = 0
    for wid, weakness in trwm_data.get("weaknesses", {}).items():
        if is_temp_id(wid):
            weakness_idx += 1
            placeholder = f"DFW-____-{weakness_idx}"
            placeholder_map[wid] = placeholder
            new_items["weaknesses"].append(weakness)
        else:
            existing_items["weaknesses"].append(weakness)

    # Process mitigations
    mitigation_idx = 0
    for mid, mitigation in trwm_data.get("mitigations", {}).items():
        if is_temp_id(mid):
            mitigation_idx += 1
            placeholder = f"DFM-____-{mitigation_idx}"
            placeholder_map[mid] = placeholder
            new_items["mitigations"].append(mitigation)
        else:
            existing_items["mitigations"].append(mitigation)

    return placeholder_map, new_items, existing_items


def apply_placeholders(item, placeholder_map):
    """Replace all temp IDs in an item with their placeholders."""
    item_json = json.dumps(item)
    for temp_id, placeholder in placeholder_map.items():
        item_json = item_json.replace(temp_id, placeholder)
    return json.loads(item_json)


def verify_existing_ids(existing_items, kb):
    """Verify that existing (real) IDs actually exist in the KB.

    Returns a list of warning strings for IDs that don't exist.
    """
    warnings = []

    for technique in existing_items.get("techniques", []):
        tid = technique.get("id", "")
        if REAL_TECHNIQUE_RE.match(tid) and kb.get_technique(tid) is None:
            warnings.append(f"Technique **{tid}** not found in knowledge base")

    for weakness in existing_items.get("weaknesses", []):
        wid = weakness.get("id", "")
        if REAL_WEAKNESS_RE.match(wid) and kb.get_weakness(wid) is None:
            warnings.append(f"Weakness **{wid}** not found in knowledge base")

    for mitigation in existing_items.get("mitigations", []):
        mid = mitigation.get("id", "")
        if REAL_MITIGATION_RE.match(mid) and kb.get_mitigation(mid) is None:
            warnings.append(f"Mitigation **{mid}** not found in knowledge base")

    # Also check cross-references within new items
    # Collect all real IDs referenced in mitigations lists of new weaknesses
    all_referenced = set()
    for weakness in existing_items.get("weaknesses", []) + \
                     [w for w in [] if False]:  # placeholder, real refs checked below
        pass

    return warnings


def collect_referenced_real_ids(trwm_data):
    """Collect all real IDs referenced in cross-references (not as top-level items)."""
    referenced = set()

    # Check technique weakness lists
    for tid, technique in trwm_data.get("techniques", {}).items():
        for wid in technique.get("weaknesses", []):
            if not is_temp_id(wid):
                referenced.add(wid)

    # Check weakness mitigation lists
    for wid, weakness in trwm_data.get("weaknesses", {}).items():
        for mid in weakness.get("mitigations", []):
            if not is_temp_id(mid):
                referenced.add(mid)

    return referenced


def verify_all_references(trwm_data, kb):
    """Verify all real IDs referenced anywhere in the submission."""
    warnings = []
    referenced = collect_referenced_real_ids(trwm_data)

    for ref_id in sorted(referenced):
        if REAL_TECHNIQUE_RE.match(ref_id):
            if kb.get_technique(ref_id) is None:
                warnings.append(f"Referenced technique **{ref_id}** not found in knowledge base")
        elif REAL_WEAKNESS_RE.match(ref_id):
            if kb.get_weakness(ref_id) is None:
                warnings.append(f"Referenced weakness **{ref_id}** not found in knowledge base")
        elif REAL_MITIGATION_RE.match(ref_id):
            if kb.get_mitigation(ref_id) is None:
                warnings.append(f"Referenced mitigation **{ref_id}** not found in knowledge base")

    return warnings


URL_PATTERN = re.compile(r'^https?://')
KNOWN_CASE_PREFIXES = [
    "https://ontology.unifiedcyberontology.org/uco/",
    "https://ontology.caseontology.org/case/",
    "https://ontology.solveit-df.org/solveit/",
    "https://cacontology.projectvic.org/",
]
def validate_submission(trwm_data, new_items):
    """Run lightweight validation checks on the submission.

    Returns a list of (level, message) tuples where level is
    'warning' or 'info'.
    """
    notes = []

    # Check CASE classes
    for tid, technique in trwm_data.get("techniques", {}).items():
        for field in ("CASE_input_classes", "CASE_output_classes"):
            for value in technique.get(field, []):
                if not URL_PATTERN.match(value):
                    notes.append((
                        "warning",
                        f"**{field}**: `{value}` is not a valid URL — "
                        f"CASE/UCO classes should be full ontology IRIs "
                        f"(e.g. `https://ontology.unifiedcyberontology.org/uco/observable/...`)"
                    ))
                elif not any(value.startswith(p) for p in KNOWN_CASE_PREFIXES):
                    notes.append((
                        "warning",
                        f"**{field}**: `{value}` does not match a known ontology prefix"
                    ))

    # Check for techniques with no description
    for technique in new_items["techniques"]:
        if not technique.get("description", "").strip():
            notes.append((
                "warning",
                f"Technique **{technique['name']}** has no description"
            ))
        if not technique.get("weaknesses"):
            notes.append((
                "warning",
                f"Technique **{technique['name']}** has no weaknesses listed"
            ))

    # Check for weaknesses with no weakness class
    for weakness in new_items["weaknesses"]:
        if not weakness.get("categories"):
            notes.append((
                "warning",
                f"Weakness **{weakness['name']}** has no ASTM error class selected"
            ))

    # Check for weaknesses with no mitigations
    no_mitigation_count = 0
    for weakness in new_items["weaknesses"]:
        if not weakness.get("mitigations"):
            no_mitigation_count += 1
    if no_mitigation_count:
        notes.append((
            "info",
            f"{no_mitigation_count} weakness(es) have no mitigations"
        ))

    # Summary counts for common optional fields
    no_ref_mitigations = sum(1 for m in new_items["mitigations"] if not m.get("references"))
    if no_ref_mitigations:
        notes.append((
            "info",
            f"{no_ref_mitigations} of {len(new_items['mitigations'])} mitigation(s) have no references"
        ))

    no_ref_weaknesses = sum(1 for w in new_items["weaknesses"] if not w.get("references"))
    if no_ref_weaknesses:
        notes.append((
            "info",
            f"{no_ref_weaknesses} of {len(new_items['weaknesses'])} weakness(es) have no references"
        ))

    return notes


def build_update_section(item_type, item_id, existing_kb, submitted):
    """Generate BEFORE/AFTER markdown for a single updated item.

    Args:
        item_type: 'technique', 'weakness', or 'mitigation'
        item_id: e.g. 'DFT-1176'
        existing_kb: dict from the KB (current version)
        submitted: dict from the submission (proposed version)

    Returns:
        list of markdown lines
    """
    lines = []
    lines.append(f"#### Updated {item_type}: {submitted.get('name', '')} (`{item_id}`)")
    lines.append("")
    lines.append("<details>")
    lines.append("<summary>BEFORE (current KB)</summary>")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(existing_kb, indent=4))
    lines.append("```")
    lines.append("</details>")
    lines.append("")
    lines.append("<details open>")
    lines.append("<summary>AFTER (proposed)</summary>")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(submitted, indent=4))
    lines.append("```")
    lines.append("</details>")
    lines.append("")

    # Change summary
    changes = build_change_summary(existing_kb, submitted)
    lines.append("**Changes:** " + " | ".join(changes) if len(changes) == 1
                 else "**Changes:**")
    if len(changes) > 1:
        lines.extend(changes)
    lines.append("")
    return lines


def detect_removed_weaknesses(trwm_data, kb):
    """Detect weaknesses present in the KB technique but absent from the submission.

    Returns a list of (weakness_id, weakness_name) tuples.
    """
    removed = []
    for tid, technique in trwm_data.get("techniques", {}).items():
        if not REAL_TECHNIQUE_RE.match(tid):
            continue
        kb_technique = kb.get_technique(tid)
        if kb_technique is None:
            continue
        submitted_wids = set(technique.get("weaknesses", []))
        for wid in kb_technique.get("weaknesses", []):
            if wid not in submitted_wids:
                kb_weakness = kb.get_weakness(wid)
                name = kb_weakness.get("name", "Unknown") if kb_weakness else "Unknown"
                removed.append((wid, name))
    return removed


def build_comment(trwm_data, fields, placeholder_map, new_items, existing_items,
                  ref_warnings, submission_type, reviewer_notes=None, kb=None):
    """Build the GitHub comment markdown."""
    lines = []

    lines.append("<!-- TRWM_PREVIEW -->")
    lines.append("")
    lines.append("Thanks for your TRWM submission! Here's a preview of the proposed changes:")
    lines.append("")

    is_update = submission_type == "Update existing technique"

    # Summary table
    lines.append("### Summary")
    lines.append("")
    existing_col = "Updated" if is_update else "Existing references"
    lines.append(f"| Type | New | {existing_col} |")
    lines.append("|------|-----|---------------------|")
    lines.append(f"| Techniques | {len(new_items['techniques'])} | {len(existing_items['techniques'])} |")
    lines.append(f"| Weaknesses | {len(new_items['weaknesses'])} | {len(existing_items['weaknesses'])} |")
    lines.append(f"| Mitigations | {len(new_items['mitigations'])} | {len(existing_items['mitigations'])} |")
    lines.append("")

    # Objective info
    objective = fields.get("Objective", "").strip()
    if objective and objective != "_No response_" and objective != "Other (specify below)":
        lines.append(f"**Objective:** {objective}")
        lines.append("")
    elif objective == "Other (specify below)":
        other_objective = fields.get("Propose new objective", "").strip()
        if other_objective and other_objective != "_No response_":
            lines.append(f"**Proposed new objective:** {other_objective}")
            lines.append("")

    # Reviewer notes — combine ref warnings and validation notes
    all_warnings = [(w, "warning") for w in ref_warnings]
    if reviewer_notes:
        all_warnings += [(msg, level) for level, msg in reviewer_notes]

    if all_warnings:
        lines.append("### Reviewer notes")
        lines.append("")
        for msg, level in all_warnings:
            icon = ":warning:" if level == "warning" else ":information_source:"
            lines.append(f"- {icon} {msg}")
        lines.append("")

    # Technique JSON blocks
    lines.append("---")
    lines.append("")
    for technique in new_items["techniques"]:
        placeholder = placeholder_map[technique["id"]]
        kb_technique = normalize_to_kb_schema(
            apply_placeholders(technique, placeholder_map),
            TECHNIQUE_FIELDS,
        )
        label = "New technique" if submission_type == "New technique" else "Update technique"
        lines.append(f"### {label}: {technique['name']} (`{placeholder}`)")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(kb_technique, indent=4))
        lines.append("```")
        lines.append("")

    # Existing technique references / updates
    for technique in existing_items["techniques"]:
        if is_update and kb:
            kb_item = kb.get_technique(technique["id"])
            if kb_item:
                submitted = normalize_to_kb_schema(
                    apply_placeholders(technique, placeholder_map),
                    TECHNIQUE_FIELDS,
                )
                lines.extend(build_update_section(
                    "technique", technique["id"], kb_item, submitted))
            else:
                lines.append(f"### Existing technique: {technique.get('name', '')} (`{technique['id']}`)")
                lines.append("")
                lines.append(f"This is an existing technique in the knowledge base. "
                              f"Weaknesses and mitigations below will be linked to it.")
                lines.append("")
        else:
            lines.append(f"### Existing technique: {technique.get('name', '')} (`{technique['id']}`)")
            lines.append("")
            lines.append(f"This is an existing technique in the knowledge base. "
                          f"Weaknesses and mitigations below will be linked to it.")
            lines.append("")

    # Weakness JSON blocks
    if new_items["weaknesses"]:
        lines.append("---")
        lines.append("")
        lines.append(f"### New weaknesses ({len(new_items['weaknesses'])})")
        lines.append("")

        for weakness in new_items["weaknesses"]:
            placeholder = placeholder_map[weakness["id"]]
            kb_weakness = normalize_to_kb_schema(
                apply_placeholders(weakness, placeholder_map),
                WEAKNESS_FIELDS,
            )
            lines.append(f"#### {weakness['name']} (`{placeholder}`)")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(kb_weakness, indent=4))
            lines.append("```")
            lines.append("")

    # Mitigation JSON blocks
    if new_items["mitigations"]:
        lines.append("---")
        lines.append("")
        lines.append(f"### New mitigations ({len(new_items['mitigations'])})")
        lines.append("")

        for mitigation in new_items["mitigations"]:
            placeholder = placeholder_map[mitigation["id"]]
            kb_mitigation = normalize_to_kb_schema(
                apply_placeholders(mitigation, placeholder_map),
                MITIGATION_FIELDS,
            )
            lines.append(f"#### {mitigation['name']} (`{placeholder}`)")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(kb_mitigation, indent=4))
            lines.append("```")
            lines.append("")

    # Existing item references — for updates, show BEFORE/AFTER; otherwise just list
    if is_update and kb:
        # Show BEFORE/AFTER for updated weaknesses and mitigations
        if existing_items["weaknesses"]:
            lines.append("---")
            lines.append("")
            lines.append(f"### Updated weaknesses ({len(existing_items['weaknesses'])})")
            lines.append("")
            for weakness in existing_items["weaknesses"]:
                kb_item = kb.get_weakness(weakness["id"])
                if kb_item:
                    submitted = normalize_to_kb_schema(
                        apply_placeholders(weakness, placeholder_map),
                        WEAKNESS_FIELDS,
                    )
                    lines.extend(build_update_section(
                        "weakness", weakness["id"], kb_item, submitted))
                else:
                    lines.append(f"- `{weakness['id']}` — {weakness.get('name', 'Unknown')} "
                                  f"(not found in KB)")
                    lines.append("")

        if existing_items["mitigations"]:
            lines.append("---")
            lines.append("")
            lines.append(f"### Updated mitigations ({len(existing_items['mitigations'])})")
            lines.append("")
            for mitigation in existing_items["mitigations"]:
                kb_item = kb.get_mitigation(mitigation["id"])
                if kb_item:
                    submitted = normalize_to_kb_schema(
                        apply_placeholders(mitigation, placeholder_map),
                        MITIGATION_FIELDS,
                    )
                    lines.extend(build_update_section(
                        "mitigation", mitigation["id"], kb_item, submitted))
                else:
                    lines.append(f"- `{mitigation['id']}` — {mitigation.get('name', 'Unknown')} "
                                  f"(not found in KB)")
                    lines.append("")

        # Flag removed weaknesses
        removed = detect_removed_weaknesses(trwm_data, kb)
        if removed:
            lines.append("---")
            lines.append("")
            lines.append("### Removed weaknesses")
            lines.append("")
            lines.append(":warning: The following weaknesses exist in the KB technique "
                          "but are **absent** from this submission:")
            lines.append("")
            for wid, wname in removed:
                lines.append(f"- `{wid}` — {wname}")
            lines.append("")
            lines.append("If these should be kept, add them back in the Helper before re-exporting.")
            lines.append("")
    else:
        all_existing = (existing_items["techniques"] + existing_items["weaknesses"] +
                        existing_items["mitigations"])
        if all_existing:
            lines.append("---")
            lines.append("")
            lines.append("### Existing KB references")
            lines.append("")
            lines.append("The following existing items are referenced in this submission:")
            lines.append("")
            for item in all_existing:
                lines.append(f"- `{item['id']}` — {item.get('name', 'Unknown')}")
            lines.append("")

    # Hidden ID map for the assignment script
    lines.append(f"<!-- TRWM_ID_MAP: {json.dumps(placeholder_map)} -->")
    lines.append("")

    # Footer
    lines.append("---")
    if placeholder_map:
        lines.append("*This comment was automatically generated. "
                      "IDs with `____` placeholders will be assigned during review "
                      "when the `assigned ID` label is added.*")
    else:
        lines.append("*This comment was automatically generated. "
                      "All items have existing IDs — no ID assignment needed. "
                      "Add the `autoimplement` label to create a PR.*")

    return '\n'.join(lines)


def determine_labels(new_items, existing_items, submission_type):
    """Determine labels to auto-apply based on submission content.

    Returns a list of label strings.
    """
    labels = []

    # Technique: new or update
    if new_items["techniques"]:
        labels.append("content: new technique")
    if existing_items["techniques"] or submission_type == "Update existing technique":
        labels.append("content: update technique")

    # Weaknesses
    if new_items["weaknesses"]:
        labels.append("content: new weakness")

    # Mitigations
    if new_items["mitigations"]:
        labels.append("content: new mitigation")

    return labels


def main():
    parser = argparse.ArgumentParser(
        description="Parse a TRWM submission issue and generate a preview comment",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--issue-body', type=str, help="Issue body as a string")
    group.add_argument('--issue-body-file', type=str, help="File containing the issue body")
    parser.add_argument('--project-root', type=str, default=None,
                        help="Path to SOLVE-IT project root (for KB verification)")
    parser.add_argument('--output', type=str,
                        help="Output file for the comment (default: stdout)")
    parser.add_argument('--labels-output', type=str,
                        help="Output file for auto-detected labels (one per line)")
    args = parser.parse_args()

    if args.issue_body_file:
        with open(args.issue_body_file) as f:
            body = f.read()
    else:
        body = args.issue_body

    # Parse the issue form fields
    fields = parse_issue_body(body)

    # Extract and parse the TRWM JSON
    raw_json = fields.get("TRWM Helper JSON export", "")
    if not raw_json or raw_json == "_No response_":
        print("Error: No TRWM JSON found in issue body", file=sys.stderr)
        sys.exit(1)

    json_text = extract_json_from_field(raw_json)
    try:
        trwm_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in TRWM export: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate structure
    for key in ("techniques", "weaknesses", "mitigations"):
        if key not in trwm_data:
            print(f"Error: Missing required key '{key}' in TRWM JSON", file=sys.stderr)
            sys.exit(1)

    # Build placeholder map and classify items
    placeholder_map, new_items, existing_items = build_placeholder_map(trwm_data)

    # Verify existing references against KB
    ref_warnings = []
    kb = None
    if args.project_root:
        try:
            kb = KnowledgeBase(args.project_root, 'solve-it.json')
            ref_warnings = verify_all_references(trwm_data, kb)
        except Exception as e:
            print(f"Warning: Could not load KB for verification: {e}", file=sys.stderr)
            ref_warnings.append(f"Could not verify existing references: {e}")

    # Determine submission type
    submission_type = fields.get("Submission type", "New technique").strip()

    # Run lightweight validation
    reviewer_notes = validate_submission(trwm_data, new_items)

    # Build the comment
    comment = build_comment(
        trwm_data, fields, placeholder_map, new_items, existing_items,
        ref_warnings, submission_type, reviewer_notes, kb=kb,
    )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(comment)
    else:
        print(comment)

    # Write auto-detected labels
    if args.labels_output:
        labels = determine_labels(new_items, existing_items, submission_type)
        with open(args.labels_output, 'w') as f:
            f.write('\n'.join(labels) + '\n' if labels else '')
        print(f"Auto-detected labels: {labels}", file=sys.stderr)


if __name__ == '__main__':
    main()
