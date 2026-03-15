"""
Generates the GitHub issue form YAML for a TRWM submission.

Reads objectives from solve-it.json to populate the objective dropdown.
Re-run this script whenever objectives are added to keep the form in sync.

Usage:
    python3 admin/form_generators/generate_trwm_submission_form.py
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
    lines.append("name: \"TRWM Submission\"")
    lines.append("description: Submit a technique with weaknesses and mitigations from the TRWM SOLVE-IT Helper app")
    lines.append("title: \"TRWM submission: {technique name}\"")
    lines.append("labels: [\"trwm\"]")
    lines.append("body:")

    # --- Technique name ---
    lines.append("  - type: input")
    lines.append("    id: technique-name")
    lines.append("    attributes:")
    lines.append("      label: Technique name")
    lines.append("      description: The name of the technique from your TRWM submission.")
    lines.append("      placeholder: e.g. Examination of a multiplayer game app")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Submission type ---
    lines.append("  - type: dropdown")
    lines.append("    id: submission-type")
    lines.append("    attributes:")
    lines.append("      label: Submission type")
    lines.append("      description: Is this a new technique or an update to an existing one?")
    lines.append("      options:")
    lines.append("        - New technique")
    lines.append("        - Update existing technique")
    lines.append("    validations:")
    lines.append("      required: true")

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

    # --- TRWM JSON ---
    lines.append("  - type: textarea")
    lines.append("    id: trwm-json")
    lines.append("    attributes:")
    lines.append("      label: TRWM Helper JSON export")
    lines.append("      description: Paste the full JSON export from the TRWM SOLVE-IT Helper app here.")
    lines.append("      render: json")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Additional notes ---
    lines.append("  - type: textarea")
    lines.append("    id: additional-notes")
    lines.append("    attributes:")
    lines.append("      label: Additional notes")
    lines.append("      description: Any additional information or context you'd like to provide.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '3_propose-trwm-submission-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  {len(objectives)} objectives")


if __name__ == '__main__':
    main()
