"""
Generates the GitHub issue form YAML for proposing a new technique.

Reads objectives from solve-it.json and weaknesses from data/weaknesses/
to populate dropdown options. Re-run this script whenever objectives or
weaknesses are added to keep the form in sync.

Usage:
    python3 admin/generate_issue_form.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solve_it_library import KnowledgeBase


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    # Collect objectives
    objectives = [obj.get('name') for obj in kb.list_objectives()]

    # Collect weaknesses as "W1001: Name" strings
    weaknesses = []
    for w_id in sorted(kb.list_weaknesses()):
        w = kb.get_weakness(w_id)
        weaknesses.append(f"{w_id}: {w['name']}")

    # Build the YAML
    lines = []
    lines.append("name: \"Propose New Technique (Form)\"")
    lines.append("description: Propose a new technique using a structured form")
    lines.append("title: \"Create new technique: [technique name]\"")
    lines.append("labels: [\"content: new technique\"]")
    lines.append("body:")

    # --- Technique name ---
    lines.append("  - type: input")
    lines.append("    id: technique-name")
    lines.append("    attributes:")
    lines.append("      label: Technique name")
    lines.append("      placeholder: e.g. Disk imaging")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Description ---
    lines.append("  - type: textarea")
    lines.append("    id: description")
    lines.append("    attributes:")
    lines.append("      label: Description")
    lines.append("      description: A short description of the technique.")
    lines.append("      placeholder: Describe what this technique does")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Synonyms ---
    lines.append("  - type: input")
    lines.append("    id: synonyms")
    lines.append("    attributes:")
    lines.append("      label: Synonyms")
    lines.append("      description: Other names that might be used for this technique (comma-separated).")
    lines.append("      placeholder: e.g. RAM dump, memory dump")

    # --- Details ---
    lines.append("  - type: textarea")
    lines.append("    id: details")
    lines.append("    attributes:")
    lines.append("      label: Details")
    lines.append("      description: Extended details about the technique.")

    # --- Examples ---
    lines.append("  - type: textarea")
    lines.append("    id: examples")
    lines.append("    attributes:")
    lines.append("      label: Examples")
    lines.append("      description: Tools or cases where this technique is used (one per line).")
    lines.append("      placeholder: |")
    lines.append("        FTK Imager")
    lines.append("        Magnet ACQUIRE")

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

    # --- Existing weaknesses (5 dropdowns) ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        ## Weaknesses")
    lines.append("        Select any existing weaknesses that apply to this technique, and/or propose new ones below.")

    for i in range(1, 6):
        lines.append(f"  - type: dropdown")
        lines.append(f"    id: existing-weakness-{i}")
        lines.append(f"    attributes:")
        lines.append(f"      label: \"Existing weakness {i}\"")
        lines.append(f"      options:")
        lines.append(f"        - \"N/A\"")
        for w in weaknesses:
            # Escape any double quotes in weakness names
            escaped = w.replace('"', '\\"')
            lines.append(f"        - \"{escaped}\"")

    # --- New weaknesses (5 text fields) ---
    for i in range(1, 6):
        lines.append(f"  - type: input")
        lines.append(f"    id: new-weakness-{i}")
        lines.append(f"    attributes:")
        lines.append(f"      label: \"Propose new weakness {i}\"")
        lines.append(f"      description: Briefly describe a new weakness for this technique.")

    # --- CASE input classes ---
    lines.append("  - type: textarea")
    lines.append("    id: case-input")
    lines.append("    attributes:")
    lines.append("      label: CASE input classes")
    lines.append("      description: |")
    lines.append("        Refer to [CASE Ontology A-Z](https://ontology.caseontology.org/documentation/entities-az.html)")
    lines.append("        or the [SOLVE-IT Ontology](https://github.com/SOLVE-IT-DF/solve-it-ontology) for suitable classes.")
    lines.append("      placeholder: e.g. https://ontology.unifiedcyberontology.org/uco/observable/File")

    # --- CASE output classes ---
    lines.append("  - type: textarea")
    lines.append("    id: case-output")
    lines.append("    attributes:")
    lines.append("      label: CASE output classes")
    lines.append("      description: |")
    lines.append("        Refer to [CASE Ontology A-Z](https://ontology.caseontology.org/documentation/entities-az.html)")
    lines.append("        or the [SOLVE-IT Ontology](https://github.com/SOLVE-IT-DF/solve-it-ontology) for suitable classes.")
    lines.append("      placeholder: e.g. https://ontology.unifiedcyberontology.org/uco/observable/Message")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: Academic or other references to support the technique (one per line).")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', 'propose-new-technique-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  {len(objectives)} objectives, {len(weaknesses)} weaknesses")


if __name__ == '__main__':
    main()
