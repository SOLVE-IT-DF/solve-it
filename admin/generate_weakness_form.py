"""
Generates the GitHub issue form YAML for proposing a new weakness.

Usage:
    python3 admin/generate_weakness_form.py
"""

import os


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..')

    lines = []
    lines.append('name: "Propose New Weakness (Form)"')
    lines.append("description: Propose a new weakness using a structured form")
    lines.append('title: "Create new weakness: [weakness name]"')
    lines.append('labels: ["content: new weakness", "form input"]')
    lines.append("body:")

    # --- Weakness name ---
    lines.append("  - type: input")
    lines.append("    id: weakness-name")
    lines.append("    attributes:")
    lines.append("      label: Weakness name")
    lines.append("      placeholder: Give this weakness a name")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Description ---
    lines.append("  - type: textarea")
    lines.append("    id: description")
    lines.append("    attributes:")
    lines.append("      label: Description")
    lines.append("      description: A longer description of the nature of the weakness.")

    # --- ASTM error classes ---
    lines.append("  - type: checkboxes")
    lines.append("    id: astm-error-classes")
    lines.append("    attributes:")
    lines.append("      label: ASTM error classes")
    lines.append("      description: Select all ASTM error classes that apply to this weakness.")
    lines.append("      options:")
    lines.append("        - label: \"INCOMP - Incomplete extraction or examination of digital evidence\"")
    lines.append("        - label: \"INAC-EX - Inaccurate examination or interpretation of extracted data\"")
    lines.append("        - label: \"INAC-AS - Using inappropriate or inaccurate assumptions to draw inferences\"")
    lines.append("        - label: \"INAC-ALT - Failure to consider alternative explanations\"")
    lines.append("        - label: \"INAC-COR - Inaccurate correlation of data from multiple sources\"")
    lines.append("        - label: \"MISINT - Misinterpretation of results by others\"")

    # --- Existing mitigation IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: existing-mitigations")
    lines.append("    attributes:")
    lines.append("      label: Existing mitigation IDs")
    lines.append("      description: IDs of existing mitigations that apply to this weakness (one per line, e.g. M1001, M1012).")
    lines.append("      render: text")

    # --- Propose new mitigations ---
    lines.append("  - type: textarea")
    lines.append("    id: new-mitigations")
    lines.append("    attributes:")
    lines.append("      label: Propose new mitigations")
    lines.append("      description: Describe new mitigations for this weakness (one per line).")
    lines.append("      render: text")

    # --- Relevant technique IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: relevant-techniques")
    lines.append("    attributes:")
    lines.append("      label: Relevant technique IDs")
    lines.append("      description: Techniques that this weakness applies to (one per line, e.g. T1001, T1028).")
    lines.append("      render: text")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: Academic or other references to support the weakness (one per line).")
    lines.append("      render: text")

    # --- Any other notes ---
    lines.append("  - type: textarea")
    lines.append("    id: other-notes")
    lines.append("    attributes:")
    lines.append("      label: Any other notes")
    lines.append("      description: Any additional information or context you'd like to provide.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', 'propose-new-weakness-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
