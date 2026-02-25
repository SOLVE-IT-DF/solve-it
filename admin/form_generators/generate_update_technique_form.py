"""
Generates the GitHub issue form YAML for proposing an update to an existing technique.

Usage:
    python3 admin/generate_update_technique_form.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from solve_it_library import KnowledgeBase


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    # Collect technique IDs and names for the dropdown
    technique_ids = kb.list_techniques()
    id_range = f"{technique_ids[0]}–{technique_ids[-1]}" if technique_ids else "T1001–T1099"
    technique_options = []
    for tid in technique_ids:
        t = kb.get_technique(tid)
        name = t.get("name", "") if t else ""
        technique_options.append(f"{tid}: {name}" if name else tid)

    lines = []
    lines.append('name: "Update Technique"')
    lines.append("description: Propose changes to an existing technique")
    lines.append('title: "Update technique: [Txxxx: technique name]"')
    lines.append('labels: ["content: update technique", "form input"]')
    lines.append("body:")

    # --- Instructions ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        ## Update an existing technique")
    lines.append("        Use this form to propose changes to an existing technique.")
    lines.append("        **Leave fields blank to keep current values.** Only fill in fields you want to change.")
    lines.append(f"        Existing techniques ({id_range}) can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/techniques).")

    # --- Technique ID ---
    lines.append("  - type: dropdown")
    lines.append("    id: technique-id")
    lines.append("    attributes:")
    lines.append("      label: Technique ID")
    lines.append("      description: Select the technique to update.")
    lines.append("      options:")
    for opt in technique_options:
        lines.append(f'        - "{opt}"')
    lines.append("    validations:")
    lines.append("      required: true")

    # --- New technique name ---
    lines.append("  - type: input")
    lines.append("    id: new-technique-name")
    lines.append("    attributes:")
    lines.append("      label: New technique name")
    lines.append("      description: Leave blank to keep the current name.")

    # --- New description ---
    lines.append("  - type: textarea")
    lines.append("    id: new-description")
    lines.append("    attributes:")
    lines.append("      label: New description")
    lines.append("      description: Leave blank to keep the current description.")
    lines.append("      render: text")

    # --- New details ---
    lines.append("  - type: textarea")
    lines.append("    id: new-details")
    lines.append("    attributes:")
    lines.append("      label: New details")
    lines.append("      description: Leave blank to keep the current details.")
    lines.append("      render: text")

    # --- Synonyms ---
    lines.append("  - type: textarea")
    lines.append("    id: synonyms")
    lines.append("    attributes:")
    lines.append("      label: Synonyms")
    lines.append("      description: |")
    lines.append("        The complete new list of synonyms (one per line).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("      render: text")

    # --- Examples ---
    lines.append("  - type: textarea")
    lines.append("    id: examples")
    lines.append("    attributes:")
    lines.append("      label: Examples")
    lines.append("      description: |")
    lines.append("        The complete new list of examples (one per line, e.g. FTK Imager, Magnet ACQUIRE).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("      render: text")

    # --- Subtechnique IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: subtechnique-ids")
    lines.append("    attributes:")
    lines.append("      label: Subtechnique IDs")
    lines.append("      description: |")
    lines.append("        The complete new list of subtechnique IDs (one per line, e.g. T1002.1, T1002.2).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append(f"        Existing techniques ({id_range}) can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/techniques).")
    lines.append("      render: text")

    # --- Weakness IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: weakness-ids")
    lines.append("    attributes:")
    lines.append("      label: Weakness IDs")
    lines.append("      description: |")
    lines.append("        The complete new list of weakness IDs (one per line, e.g. W1004, W1014).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("        Existing weaknesses can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/weaknesses).")
    lines.append("      render: text")

    # --- Proposed new weaknesses ---
    lines.append("  - type: textarea")
    lines.append("    id: new-weaknesses")
    lines.append("    attributes:")
    lines.append("      label: Propose new weaknesses")
    lines.append("      description: |")
    lines.append("        Describe new weaknesses for this technique (one per line, e.g. Imaging process may miss data in hidden areas).")
    lines.append("        These will be created as new weakness entries and linked to the technique.")
    lines.append("      render: text")

    # --- CASE input classes ---
    lines.append("  - type: textarea")
    lines.append("    id: case-input")
    lines.append("    attributes:")
    lines.append("      label: CASE input classes")
    lines.append("      description: |")
    lines.append("        The complete new list of CASE input classes (one per line).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("        Refer to [CASE Ontology A-Z](https://ontology.caseontology.org/documentation/entities-az.html)")
    lines.append("        or the [SOLVE-IT Ontology A-Z](https://ontology.solveit-df.org/entities-az.html) for suitable classes.")
    lines.append("      render: text")

    # --- CASE output classes ---
    lines.append("  - type: textarea")
    lines.append("    id: case-output")
    lines.append("    attributes:")
    lines.append("      label: CASE output classes")
    lines.append("      description: |")
    lines.append("        The complete new list of CASE output classes (one per line).")
    lines.append("        Leave blank to keep the current list. If populated, this replaces the entire list.")
    lines.append("        Refer to [CASE Ontology A-Z](https://ontology.caseontology.org/documentation/entities-az.html)")
    lines.append("        or the [SOLVE-IT Ontology A-Z](https://ontology.solveit-df.org/entities-az.html) for suitable classes.")
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
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '2a_update-technique-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  Technique ID range: {id_range}")


if __name__ == '__main__':
    main()
