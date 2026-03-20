"""
Generates the GitHub issue form YAML for proposing a new weakness.

Usage:
    python3 admin/generate_weakness_form.py
"""

import os


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')

    lines = []
    lines.append('name: "Propose New Weakness"')
    lines.append("description: Propose a new weakness using a structured form")
    lines.append('title: "Create new weakness: [weakness name]"')
    lines.append('labels: ["content: new weakness", "form input"]')
    lines.append("body:")

    # --- Weakness name ---
    lines.append("  - type: input")
    lines.append("    id: weakness-name")
    lines.append("    attributes:")
    lines.append("      label: Weakness name")
    lines.append("      description: A suggested, fairly short name for the weakness.")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Description ---
    lines.append("  - type: textarea")
    lines.append("    id: description")
    lines.append("    attributes:")
    lines.append("      label: Description")
    lines.append("      description: A longer description of the nature of the weakness.")
    lines.append("      render: text")

    # --- Categories ---
    lines.append("  - type: textarea")
    lines.append("    id: categories")
    lines.append("    attributes:")
    lines.append("      label: Categories")
    lines.append("      description: 'Enter one class code per line. Valid codes — ASTM_INCOMP (Incompleteness), ASTM_INAC_EX (Inaccuracy: Existence), ASTM_INAC_AS (Inaccuracy: Association), ASTM_INAC_ALT (Inaccuracy: Alteration), ASTM_INAC_COR (Inaccuracy: Corruption), ASTM_MISINT (Misinterpretation).'")
    lines.append("      placeholder: Enter one class code per line")

    # --- Existing mitigation IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: existing-mitigations")
    lines.append("    attributes:")
    lines.append("      label: Existing mitigation IDs")
    lines.append("      description: IDs of existing mitigations that apply to this weakness (one per line, e.g. DFM-1001, DFM-1012).")
    lines.append("      placeholder: Enter one mitigation ID per line")
    lines.append("      render: text")

    # --- Propose new mitigations ---
    lines.append("  - type: textarea")
    lines.append("    id: new-mitigations")
    lines.append("    attributes:")
    lines.append("      label: Propose new mitigations")
    lines.append("      description: Describe new mitigations for this weakness (one per line).")
    lines.append("      placeholder: Enter one mitigation description per line")
    lines.append("      render: text")

    # --- Techniques this applies to ---
    lines.append("  - type: textarea")
    lines.append("    id: relevant-techniques")
    lines.append("    attributes:")
    lines.append("      label: Techniques this applies to")
    lines.append("      description: Techniques that this weakness applies to (one per line, e.g. DFT-1001, DFT-1028).")
    lines.append("      placeholder: Enter one technique ID per line")
    lines.append("      render: text")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: |")
    lines.append("        Existing DFCite IDs, one per line. If you need to add a new reference, please use the Propose New Reference form first.")
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
    lines.append("      description: Any additional information or context you'd like to provide.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '1b_propose-new-weakness-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
