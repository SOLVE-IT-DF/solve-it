"""
Patches dynamic content in GitHub issue form YAML files.

The YAML files in .github/ISSUE_TEMPLATE/ are the source of truth for form
content. This script only updates the parts that are derived from the knowledge
base:

  1. Objective dropdown options — in 1a (new technique) and 3 (TRWM)
  2. Objective ID reference list — in 2e (move technique)

Run this script whenever objectives are added or renamed.

Usage:
    python3 admin/form_generators/patch_forms.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from solve_it_library import KnowledgeBase


def patch_objective_dropdown(yaml_text, objective_names):
    """Replace the options list under a dropdown with id: objective."""
    # Match the options block under id: objective, up to the next field or
    # section at the same indentation level.  The dropdown looks like:
    #
    #   - type: dropdown
    #     id: objective
    #     attributes:
    #       ...
    #       options:
    #         - "Obj 1"
    #         - "Obj 2"
    #         - Other (specify below)
    #     validations:
    #
    # We replace everything between "options:" and the next line that is NOT
    # an option entry (i.e. not matching /^\s+- /).

    new_options = ''.join(
        f'        - "{name}"\n' for name in objective_names
    )
    new_options += '        - Other (specify below)\n'

    # Anchor to the objective dropdown specifically (id: objective)
    pattern = re.compile(
        r'(    id: objective\n'       # the id line
        r'    attributes:\n'          # attributes key
        r'      label: Objective\n'   # label
        r'      description: [^\n]+\n'  # description line
        r'      options:\n)'          # options key
        r'((?:        - .+\n)+)',     # one or more option lines
        re.MULTILINE,
    )

    patched, count = pattern.subn(r'\g<1>' + new_options, yaml_text)
    return patched, count


def patch_objective_id_list(yaml_text, objectives):
    """Replace the objective ID reference list in the move technique form."""
    new_list = ''.join(
        f"        - `{obj.get('id')}` \u2014 {obj.get('name')}\n"
        for obj in objectives
    )

    pattern = re.compile(
        r'(\*\*Objective IDs for reference:\*\*\n)'
        r'((?:        - `.+` \u2014 .+\n)+)',
        re.MULTILINE,
    )

    patched, count = pattern.subn(r'\g<1>' + new_list, yaml_text)
    return patched, count


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    kb = KnowledgeBase(base_path, 'solve-it.json')

    objectives = kb.list_objectives()
    objective_names = [obj.get('name') for obj in objectives]

    template_dir = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE')

    # --- 1. Patch objective dropdowns in 1a and 3 ---
    dropdown_forms = [
        '1a_propose-new-technique-form.yml',
        '3_propose-trwm-submission-form.yml',
    ]

    for filename in dropdown_forms:
        path = os.path.join(template_dir, filename)
        with open(path) as f:
            text = f.read()

        patched, count = patch_objective_dropdown(text, objective_names)

        if count == 0:
            print(f"WARNING: No objective dropdown found in {filename}")
            continue

        if patched != text:
            with open(path, 'w') as f:
                f.write(patched)
            print(f"Patched objective dropdown in {filename} ({len(objective_names)} objectives)")
        else:
            print(f"No changes needed in {filename} (already up to date)")

    # --- 2. Patch objective ID list in 2e ---
    move_form = '2e_move-technique-form.yml'
    path = os.path.join(template_dir, move_form)
    with open(path) as f:
        text = f.read()

    patched, count = patch_objective_id_list(text, objectives)

    if count == 0:
        print(f"WARNING: No objective ID list found in {move_form}")
    elif patched != text:
        with open(path, 'w') as f:
            f.write(patched)
        print(f"Patched objective ID list in {move_form} ({len(objectives)} objectives)")
    else:
        print(f"No changes needed in {move_form} (already up to date)")


if __name__ == '__main__':
    main()
