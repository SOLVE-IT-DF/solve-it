"""
Generates the GitHub issue form YAML for proposing a new mitigation.

Usage:
    python3 admin/generate_mitigation_form.py
"""

import os


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..')

    lines = []
    lines.append('name: "Propose New Mitigation (Form)"')
    lines.append("description: Propose a new mitigation using a structured form")
    lines.append('title: "Create new mitigation: [mitigation name]"')
    lines.append('labels: ["content: new mitigation", "form input"]')
    lines.append("body:")

    # --- Mitigation name ---
    lines.append("  - type: input")
    lines.append("    id: mitigation-name")
    lines.append("    attributes:")
    lines.append("      label: Mitigation name")
    lines.append("      placeholder: Give this mitigation a name")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Description ---
    lines.append("  - type: textarea")
    lines.append("    id: description")
    lines.append("    attributes:")
    lines.append("      label: Description")
    lines.append("      description: A longer description of the mitigation.")

    # --- Linked technique ---
    lines.append("  - type: input")
    lines.append("    id: linked-technique")
    lines.append("    attributes:")
    lines.append("      label: Linked technique")
    lines.append("      description: Some mitigations are links to techniques. Provide the technique ID if applicable (e.g. T1028).")
    lines.append("      placeholder: Technique ID (if applicable)")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: Academic or other references to support the mitigation (one per line).")
    lines.append("      render: text")

    # --- Any other notes ---
    lines.append("  - type: textarea")
    lines.append("    id: other-notes")
    lines.append("    attributes:")
    lines.append("      label: Any other notes")
    lines.append("      description: Any additional information or context you'd like to provide.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', 'propose-new-mitigation-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
