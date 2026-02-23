"""
Generates the GitHub issue form YAML for proposing a new technique.

Reads objectives from solve-it.json to populate the objective dropdown.
Re-run this script whenever objectives are added to keep the form in sync.

Usage:
    python3 admin/generate_technique_form.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from solve_it_library import KnowledgeBase


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    # Collect objectives
    objectives = [obj.get('name') for obj in kb.list_objectives()]

    # Build the YAML
    lines = []
    lines.append("name: \"Propose New Technique (Form)\"")
    lines.append("description: Propose a new technique using a structured form")
    lines.append("title: \"Create new technique: [technique name]\"")
    lines.append("labels: [\"content: new technique\", \"form input\"]")
    lines.append("body:")

    # --- Technique name ---
    lines.append("  - type: input")
    lines.append("    id: technique-name")
    lines.append("    attributes:")
    lines.append("      label: Technique name")
    lines.append("      description: The name for the technique (synonyms can be provided below).")
    lines.append("      placeholder: Give this technique a name")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Description ---
    lines.append("  - type: textarea")
    lines.append("    id: description")
    lines.append("    attributes:")
    lines.append("      label: Description")
    lines.append("      description: A short description of the technique (extended details can be provided below).")
    lines.append("      render: text")
    lines.append("      placeholder: Describe what this technique does")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Synonyms ---
    lines.append("  - type: textarea")
    lines.append("    id: synonyms")
    lines.append("    attributes:")
    lines.append("      label: Synonyms")
    lines.append("      description: Other names that might be used for this technique (one per line, e.g. RAM dump, memory dump).")
    lines.append("      render: text")

    # --- Details ---
    lines.append("  - type: textarea")
    lines.append("    id: details")
    lines.append("    attributes:")
    lines.append("      label: Details")
    lines.append("      description: A longer set of details can be provided to describe the technique.")
    lines.append("      render: text")

    # --- Examples ---
    lines.append("  - type: textarea")
    lines.append("    id: examples")
    lines.append("    attributes:")
    lines.append("      label: Examples")
    lines.append("      description: Examples of cases where the technique can be used, or tools that offer the technique (one per line, e.g. FTK Imager, Magnet ACQUIRE).")
    lines.append("      render: text")

    # --- Objective dropdown ---
    lines.append("  - type: dropdown")
    lines.append("    id: objective")
    lines.append("    attributes:")
    lines.append("      label: Objective")
    lines.append("      description: Which objective does this technique fit under?")
    lines.append("      options:")
    for obj in objectives:
        lines.append(f"        - \"{obj}\"")
    lines.append("        - Other (specify below)")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Objective free text ---
    lines.append("  - type: input")
    lines.append("    id: objective-other")
    lines.append("    attributes:")
    lines.append("      label: Propose new objective")
    lines.append("      description: If your technique doesn't fit an existing objective, propose one here.")

    # --- Weaknesses section ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        ## Weaknesses")
    lines.append("        List any existing weakness IDs that apply, and/or propose new weaknesses below.")
    lines.append("        Existing weaknesses can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/weaknesses).")

    # --- Existing weakness IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: existing-weaknesses")
    lines.append("    attributes:")
    lines.append("      label: Existing weakness IDs")
    lines.append("      description: IDs of existing weaknesses that apply to this technique (one per line, e.g. W1004, W1014).")
    lines.append("      render: text")

    # --- Proposed new weaknesses ---
    lines.append("  - type: textarea")
    lines.append("    id: new-weaknesses")
    lines.append("    attributes:")
    lines.append("      label: Propose new weaknesses")
    lines.append("      description: Describe new weaknesses for this technique (one per line, e.g. Imaging process may miss data in hidden areas).")
    lines.append("      render: text")

    # --- CASE input classes ---
    lines.append("  - type: textarea")
    lines.append("    id: case-input")
    lines.append("    attributes:")
    lines.append("      label: CASE input classes")
    lines.append("      description: |")
    lines.append("        Refer to [CASE Ontology A-Z](https://ontology.caseontology.org/documentation/entities-az.html)")
    lines.append("        or the [SOLVE-IT Ontology A-Z](https://ontology.solveit-df.org/entities-az.html) for suitable classes (one per line).")
    lines.append("      render: text")

    # --- CASE output classes ---
    lines.append("  - type: textarea")
    lines.append("    id: case-output")
    lines.append("    attributes:")
    lines.append("      label: CASE output classes")
    lines.append("      description: |")
    lines.append("        Refer to [CASE Ontology A-Z](https://ontology.caseontology.org/documentation/entities-az.html)")
    lines.append("        or the [SOLVE-IT Ontology A-Z](https://ontology.solveit-df.org/entities-az.html) for suitable classes (one per line).")
    lines.append("        You can also propose a new CASE class via the [CASE Issue Tracker](https://github.com/casework/CASE/issues).")
    lines.append("      render: text")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: References to support any details provided above (one per line).")
    lines.append("      render: text")

    # --- Any other notes ---
    lines.append("  - type: textarea")
    lines.append("    id: other-notes")
    lines.append("    attributes:")
    lines.append("      label: Any other notes")
    lines.append("      description: Any additional information or context you'd like to provide.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '1a_propose-new-technique-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  {len(objectives)} objectives")


if __name__ == '__main__':
    main()
