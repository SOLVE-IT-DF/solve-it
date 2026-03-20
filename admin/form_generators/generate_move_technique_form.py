"""
Generates the GitHub issue form YAML for proposing to move a technique.

The form is kept simple: the user provides the technique to move (DFT-xxxx)
and the destination (DFO-xxxx or DFT-xxxx). The parser infers the move type
from the ID prefixes:
  - DFT → DFO = move/promote technique to an objective
  - DFT → DFT = demote technique to be a subtechnique of another technique

Usage:
    python3 admin/form_generators/generate_move_technique_form.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from solve_it_library import KnowledgeBase


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    technique_ids = kb.list_techniques()
    id_range = f"{technique_ids[0]}–{technique_ids[-1]}" if technique_ids else "DFT-1001–DFT-1099"

    objectives = kb.list_objectives()
    obj_ids = [obj.get('id') for obj in objectives]
    obj_range = f"{obj_ids[0]}–{obj_ids[-1]}" if obj_ids else "DFO-1001–DFO-1021"

    # Build a reference list of objectives for the instructions
    obj_list_lines = []
    for obj in objectives:
        obj_list_lines.append(f"        - `{obj.get('id')}` — {obj.get('name')}")
    obj_list_block = '\n'.join(obj_list_lines)

    lines = []
    lines.append('name: "Move Technique"')
    lines.append("description: Propose moving a technique to a different objective or making it a subtechnique")
    lines.append('title: "Move technique: [DFT-xxxx]"')
    lines.append('labels: ["content: move technique", "form input"]')
    lines.append("body:")

    # --- Instructions ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        ## Move a technique")
    lines.append("        Provide the technique to move and where it should go.")
    lines.append("        - To move a technique under a **different objective**, set the destination to an objective ID (e.g. `DFO-1010`).")
    lines.append("        - To make a technique a **subtechnique** of another technique, set the destination to a technique ID (e.g. `DFT-1015`).")
    lines.append("        - To **promote** a subtechnique to a top-level technique, set the destination to an objective ID.")
    lines.append("")
    lines.append(f"        Existing techniques ({id_range}) can be browsed [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data/techniques) (right-click → open in new tab to keep your progress).")
    lines.append("")
    lines.append("        **Objective IDs for reference:**")
    lines.append(obj_list_block)

    # --- Technique ID ---
    lines.append("  - type: input")
    lines.append("    id: technique-id")
    lines.append("    attributes:")
    lines.append("      label: Technique to move")
    lines.append("      description: The ID of the technique to move (e.g. DFT-1002).")
    lines.append("      placeholder: DFT-xxxx")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Destination ID ---
    lines.append("  - type: input")
    lines.append("    id: destination-id")
    lines.append("    attributes:")
    lines.append("      label: Destination")
    lines.append("      description: |")
    lines.append("        The ID of the destination — either an objective (DFO-xxxx) or a parent technique (DFT-xxxx).")
    lines.append("      placeholder: DFO-xxxx or DFT-xxxx")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Rationale ---
    lines.append("  - type: textarea")
    lines.append("    id: rationale")
    lines.append("    attributes:")
    lines.append("      label: Rationale")
    lines.append("      description: Why should this technique be moved?")
    lines.append("      render: text")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Any other notes ---
    lines.append("  - type: textarea")
    lines.append("    id: other-notes")
    lines.append("    attributes:")
    lines.append("      label: Any other notes")
    lines.append("      description: Any additional information or context.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '2e_move-technique-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")
    print(f"  {len(objectives)} objectives ({obj_range})")
    print(f"  Technique ID range: {id_range}")


if __name__ == '__main__':
    main()
