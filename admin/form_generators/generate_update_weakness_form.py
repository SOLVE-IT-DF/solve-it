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

    # Collect weakness IDs and names for the dropdown
    weakness_ids = kb.list_weaknesses()
    id_range = f"{weakness_ids[0]}–{weakness_ids[-1]}" if weakness_ids else "W1001–W1099"
    weakness_options = []
    for wid in weakness_ids:
        w = kb.get_weakness(wid)
        name = w.get("name", "") if w else ""
        weakness_options.append(f"{wid}: {name}" if name else wid)

    lines = []
    lines.append('name: "Update Weakness"')
    lines.append("description: Propose changes to an existing weakness")
    lines.append('title: "Update weakness: [Wxxxx: weakness name]"')
    lines.append('labels: ["content: update weakness", "form input"]')
    lines.append("body:")

    # --- Instructions ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        ## Update an existing weakness")
    lines.append("        Use this form to propose changes to an existing weakness.")
    lines.append("        **Leave fields blank (or all unchecked) to keep current values.** Only fill in fields you want to change.")
    lines.append(f"        Existing weaknesses ({id_range}) can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/weaknesses).")

    # --- Weakness ID ---
    lines.append("  - type: dropdown")
    lines.append("    id: weakness-id")
    lines.append("    attributes:")
    lines.append("      label: Weakness ID")
    lines.append("      description: Select the weakness to update.")
    lines.append("      options:")
    for opt in weakness_options:
        lines.append(f'        - "{opt}"')
    lines.append("    validations:")
    lines.append("      required: true")

    # --- New weakness name ---
    lines.append("  - type: input")
    lines.append("    id: new-weakness-name")
    lines.append("    attributes:")
    lines.append("      label: New weakness name")
    lines.append("      description: Leave blank to keep the current name.")

    # --- ASTM error classes ---
    lines.append("  - type: checkboxes")
    lines.append("    id: astm-error-classes")
    lines.append("    attributes:")
    lines.append("      label: ASTM error classes")
    lines.append("      description: |")
    lines.append("        Select the ASTM error classes that should apply.")
    lines.append("        **Leave ALL unchecked to keep current values.** If any are checked, the selection replaces the current set.")
    lines.append("      options:")
    lines.append('        - label: "INCOMP - Incompleteness (e.g. failure to recover live or deleted artefacts, other reasons why an artefact might be missed)"')
    lines.append('        - label: "INAC-EX - Inaccuracy: Existence (e.g. presenting an artefact for something that does not exist)"')
    lines.append('        - label: "INAC-AS - Inaccuracy: Association (e.g. presenting live data as deleted and vice versa)"')
    lines.append('        - label: "INAC-ALT - Inaccuracy: Alteration (e.g. modifying the content of some digital data)"')
    lines.append('        - label: "INAC-COR - Inaccuracy: Corruption (e.g. could the process corrupt data, could the process fail to detect corrupt data)"')
    lines.append('        - label: "MISINT - Misinterpretation (e.g. could results be presented in a way that encourages misinterpretation)"')

    # --- Mitigation IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: mitigation-ids")
    lines.append("    attributes:")
    lines.append("      label: Mitigation IDs")
    lines.append("      description: |")
    lines.append("        The complete new list of mitigation IDs (one per line, e.g. M1001, M1012).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("        Existing mitigations can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/mitigations).")
    lines.append("      render: text")

    # --- Proposed new mitigations ---
    lines.append("  - type: textarea")
    lines.append("    id: new-mitigations")
    lines.append("    attributes:")
    lines.append("      label: Propose new mitigations")
    lines.append("      description: |")
    lines.append("        Describe new mitigations for this weakness (one per line).")
    lines.append("        These will be created as new mitigation entries and linked to the weakness.")
    lines.append("      render: text")

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
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '2b_update-weakness-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  Weakness ID range: {id_range}")


if __name__ == '__main__':
    main()
