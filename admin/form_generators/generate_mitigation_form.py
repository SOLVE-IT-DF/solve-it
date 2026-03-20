"""
Generates the GitHub issue form YAML for proposing a new mitigation.

Usage:
    python3 admin/generate_mitigation_form.py
"""

import os


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')

    lines = []
    lines.append('name: "Propose New Mitigation"')
    lines.append("description: Propose a new mitigation using a structured form")
    lines.append('title: "Create new mitigation: [mitigation name]"')
    lines.append('labels: ["content: new mitigation", "form input"]')
    lines.append("body:")

    # --- Mitigation name ---
    lines.append("  - type: input")
    lines.append("    id: mitigation-name")
    lines.append("    attributes:")
    lines.append("      label: Mitigation name")
    lines.append("      description: A suggested name for the mitigation.")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Description ---
    lines.append("  - type: textarea")
    lines.append("    id: description")
    lines.append("    attributes:")
    lines.append("      label: Description")
    lines.append("      description: A longer description of the mitigation.")
    lines.append("      render: text")

    # --- Existing weakness IDs ---
    lines.append("  - type: textarea")
    lines.append("    id: existing-weaknesses")
    lines.append("    attributes:")
    lines.append("      label: Existing weakness IDs")
    lines.append("      description: IDs of existing weaknesses this mitigation applies to (one per line, e.g. DFW-1001, DFW-1014).")
    lines.append("      placeholder: Enter one weakness ID per line")
    lines.append("      render: text")

    # --- Linked technique ---
    lines.append("  - type: input")
    lines.append("    id: linked-technique")
    lines.append("    attributes:")
    lines.append("      label: Linked technique")
    lines.append("      description: |")
    lines.append("        Some mitigations are links to techniques. This happens when they are complex enough to need longer descriptions, and have their own weaknesses.")
    lines.append("        Provide the technique ID if applicable (e.g. DFT-1002, see DFM-1007 for an example).")

    # --- References ---
    lines.append("  - type: textarea")
    lines.append("    id: references")
    lines.append("    attributes:")
    lines.append("      label: References")
    lines.append("      description: |")
    lines.append("        Existing DFCite IDs, one per line. If you need to add a new reference, please use the Propose New Reference form first.")
    lines.append("        You should add a relevance summary using a pipe, e.g. DFCite-xxxx | reason why this reference is useful for this mitigation (max 280 chars).")
    lines.append("      placeholder: |")
    lines.append("        Enter one reference per line")
    lines.append("        DFCite-xxxx | reason why this reference is useful for this mitigation (max 280 chars)")
    lines.append("      render: text")

    # --- Any other notes ---
    lines.append("  - type: textarea")
    lines.append("    id: other-notes")
    lines.append("    attributes:")
    lines.append("      label: Any other notes")
    lines.append("      description: Any additional information or context you'd like to provide.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '1c_propose-new-mitigation-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
