"""
Generates the GitHub issue form YAML for proposing an update to an existing weakness.

Usage:
    python3 admin/generate_update_weakness_form.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from solve_it_library import KnowledgeBase


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    # Collect weakness IDs for the description text
    weakness_ids = kb.list_weaknesses()
    id_range = f"{weakness_ids[0]}–{weakness_ids[-1]}" if weakness_ids else "DFW-1001–DFW-1099"

    lines = []
    lines.append('name: "Update Weakness"')
    lines.append("description: Propose changes to an existing weakness")
    lines.append('title: "Update weakness: [DFW-xxxx: weakness name]"')
    lines.append('labels: ["content: update weakness", "form input"]')
    lines.append("body:")

    # --- Instructions ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        ## Update an existing weakness")
    lines.append("        Use this form to propose changes to an existing weakness.")
    lines.append("        **Leave fields blank (or all unchecked) to keep current values.** Only fill in fields you want to change.")
    lines.append(f"        Existing weaknesses ({id_range}) can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/weaknesses) (right-click → open in new tab to keep your progress).")

    # --- Weakness ID ---
    lines.append("  - type: input")
    lines.append("    id: weakness-id")
    lines.append("    attributes:")
    lines.append("      label: Weakness ID")
    lines.append("      description: The ID of the weakness to update (e.g. DFW-1001).")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- New weakness name ---
    lines.append("  - type: input")
    lines.append("    id: new-weakness-name")
    lines.append("    attributes:")
    lines.append("      label: New weakness name")
    lines.append("      description: Leave blank to keep the current name.")

    # --- Categories ---
    lines.append("  - type: textarea")
    lines.append("    id: categories")
    lines.append("    attributes:")
    lines.append("      label: Categories")
    lines.append("      description: 'Enter one class code per line. Leave blank to keep current values. If populated, this replaces the entire list. Valid codes — ASTM_INCOMP (Incompleteness), ASTM_INAC_EX (Inaccuracy: Existence), ASTM_INAC_AS (Inaccuracy: Association), ASTM_INAC_ALT (Inaccuracy: Alteration), ASTM_INAC_COR (Inaccuracy: Corruption), ASTM_MISINT (Misinterpretation).'")
    lines.append("      placeholder: Enter one class code per line")

    # --- Mitigation IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: mitigation-ids")
    lines.append("    attributes:")
    lines.append("      label: Mitigation IDs")
    lines.append("      description: |")
    lines.append("        The complete new list of mitigation IDs (one per line, e.g. DFM-1001, DFM-1012).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("        Existing mitigations can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/mitigations).")
    lines.append("      placeholder: Enter one mitigation ID per line")
    lines.append("      render: text")

    # --- Proposed new mitigations ---
    lines.append("  - type: textarea")
    lines.append("    id: new-mitigations")
    lines.append("    attributes:")
    lines.append("      label: Propose new mitigations")
    lines.append("      description: |")
    lines.append("        Describe new mitigations for this weakness (one per line).")
    lines.append("        These will be created as new mitigation entries and linked to the weakness.")
    lines.append("      placeholder: Enter one mitigation description per line")
    lines.append("      render: text")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: |")
    lines.append("        The complete new list of references — existing DFCite IDs, one per line. If you need to add a new reference, please use the Propose New Reference form first.")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("        You should add a relevance summary using a pipe, e.g. DFCite-xxxx | reason why this reference is useful for this weakness (max 280 chars).")
    lines.append("      placeholder: |")
    lines.append("        Enter one reference per line")
    lines.append("        DFCite-xxxx | reason why this reference is useful for this weakness (max 280 chars)")
    lines.append("      render: text")

    # --- Any other notes ---
    lines.append("  - type: textarea")
    lines.append("    id: other-notes")
    lines.append("    attributes:")
    lines.append("      label: Any other notes")
    lines.append("      description: Any additional information or context for the proposed changes.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '2b_update-weakness-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  Weakness ID range: {id_range}")


if __name__ == '__main__':
    main()
