"""
Generates the GitHub issue form YAML for proposing a new reference.

Usage:
    python3 admin/form_generators/generate_reference_form.py
"""

import os


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')

    lines = []
    lines.append('name: "Propose New Reference"')
    lines.append("description: Propose a new reference citation for the knowledge base")
    lines.append('title: "Propose new reference: [citation]"')
    lines.append('labels: ["content: new reference", "form input"]')
    lines.append("body:")

    # --- Citation text ---
    lines.append("  - type: textarea")
    lines.append("    id: citation-text")
    lines.append("    attributes:")
    lines.append("      label: Citation text")
    lines.append("      description: The full citation text or URL for the reference.")
    lines.append("      placeholder: e.g. Author, A., 2024. Title of work. Publisher. https://example.com")
    lines.append("      render: text")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- BibTeX entry ---
    lines.append("  - type: textarea")
    lines.append("    id: bibtex-entry")
    lines.append("    attributes:")
    lines.append("      label: BibTeX entry")
    lines.append("      description: Paste BibTeX if available (optional).")
    lines.append("      render: text")

    # --- Notes ---
    lines.append("  - type: textarea")
    lines.append("    id: notes")
    lines.append("    attributes:")
    lines.append("      label: Notes")
    lines.append("      description: Any additional context about this reference.")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '3a_propose-new-reference-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
