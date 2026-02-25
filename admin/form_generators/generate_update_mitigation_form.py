"""
Generates the GitHub issue form YAML for proposing an update to an existing mitigation.

Usage:
    python3 admin/generate_update_mitigation_form.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from solve_it_library import KnowledgeBase


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    # Collect mitigation IDs and names for the dropdown
    mitigation_ids = kb.list_mitigations()
    id_range = f"{mitigation_ids[0]}–{mitigation_ids[-1]}" if mitigation_ids else "M1001–M1099"
    mitigation_options = []
    for mid in mitigation_ids:
        m = kb.get_mitigation(mid)
        name = m.get("name", "") if m else ""
        mitigation_options.append(f"{mid}: {name}" if name else mid)

    lines = []
    lines.append('name: "Update Mitigation"')
    lines.append("description: Propose changes to an existing mitigation")
    lines.append('title: "Update mitigation: [Mxxxx: mitigation name]"')
    lines.append('labels: ["content: update mitigation", "form input"]')
    lines.append("body:")

    # --- Instructions ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        ## Update an existing mitigation")
    lines.append("        Use this form to propose changes to an existing mitigation.")
    lines.append("        **Leave fields blank to keep current values.** Only fill in fields you want to change.")
    lines.append(f"        Existing mitigations ({id_range}) can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/mitigations).")

    # --- Mitigation ID ---
    lines.append("  - type: dropdown")
    lines.append("    id: mitigation-id")
    lines.append("    attributes:")
    lines.append("      label: Mitigation ID")
    lines.append("      description: Select the mitigation to update.")
    lines.append("      options:")
    for opt in mitigation_options:
        lines.append(f'        - "{opt}"')
    lines.append("    validations:")
    lines.append("      required: true")

    # --- New mitigation name ---
    lines.append("  - type: input")
    lines.append("    id: new-mitigation-name")
    lines.append("    attributes:")
    lines.append("      label: New mitigation name")
    lines.append("      description: Leave blank to keep the current name.")

    # --- Linked technique action ---
    lines.append("  - type: dropdown")
    lines.append("    id: linked-technique-action")
    lines.append("    attributes:")
    lines.append("      label: Linked technique action")
    lines.append("      description: |")
    lines.append("        Some mitigations link to a technique. Choose what to do with the linked technique.")
    lines.append("        See [M1007](https://github.com/SOLVE-IT-DF/solve-it/blob/main/data/mitigations/M1007.json) for an example.")
    lines.append("      options:")
    lines.append('        - "No change"')
    lines.append('        - "Set new value (provide ID below)"')
    lines.append('        - "Remove current link"')
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Linked technique ID ---
    lines.append("  - type: input")
    lines.append("    id: linked-technique-id")
    lines.append("    attributes:")
    lines.append("      label: Linked technique ID")
    lines.append("      description: Only used if 'Set new value' is selected above. Provide the technique ID (e.g. T1002).")
    lines.append("      placeholder: T1002")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: |")
    lines.append("        The complete new list of references (one per line).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("      render: text")

    # --- Any other notes ---
    lines.append("  - type: textarea")
    lines.append("    id: other-notes")
    lines.append("    attributes:")
    lines.append("      label: Any other notes")
    lines.append("      description: Any additional information or context for the proposed changes.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '2c_update-mitigation-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  Mitigation ID range: {id_range}")


if __name__ == '__main__':
    main()
