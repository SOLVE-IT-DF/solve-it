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
    lines.append("      description: A suggested, fairly short name for the weakness.")
    lines.append("      placeholder: Give this weakness a name")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Description ---
    lines.append("  - type: textarea")
    lines.append("    id: description")
    lines.append("    attributes:")
    lines.append("      label: Description")
    lines.append("      description: A longer description of the nature of the weakness.")
    lines.append("      render: text")

    # --- ASTM error classes ---
    lines.append("  - type: checkboxes")
    lines.append("    id: astm-error-classes")
    lines.append("    attributes:")
    lines.append("      label: ASTM error classes")
    lines.append("      description: |")
    lines.append("        Select all ASTM error classes that apply to this weakness.")
    lines.append("        If this is unclear just note if this affects any of the following properties of the results: authenticity, accuracy, completeness.")
    lines.append("      options:")
    lines.append("        - label: \"INCOMP - Incompleteness (e.g. failure to recover live or deleted artefacts, other reasons why an artefact might be missed)\"")
    lines.append("        - label: \"INAC-EX - Inaccuracy: Existence (e.g. presenting an artefact for something that does not exist)\"")
    lines.append("        - label: \"INAC-AS - Inaccuracy: Association (e.g. presenting live data as deleted and vice versa)\"")
    lines.append("        - label: \"INAC-ALT - Inaccuracy: Alteration (e.g. modifying the content of some digital data)\"")
    lines.append("        - label: \"INAC-COR - Inaccuracy: Corruption (e.g. could the process corrupt data, could the process fail to detect corrupt data)\"")
    lines.append("        - label: \"MISINT - Misinterpretation (e.g. could results be presented in a way that encourages misinterpretation)\"")

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
    lines.append("      description: References to support the details provided above (one per line).")
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
