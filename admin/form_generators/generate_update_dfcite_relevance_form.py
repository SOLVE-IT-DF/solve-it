"""
Generates the GitHub issue form YAML for updating a DFCite relevance summary.

Usage:
    python3 admin/form_generators/generate_update_dfcite_relevance_form.py
"""

import os


def main():
    base_path = os.path.join(os.path.dirname(__file__), '..', '..')

    lines = []
    lines.append('name: "Update DFCite Relevance Summary"')
    lines.append("description: Update the relevance summary for a reference citation within a technique, weakness, or mitigation")
    lines.append('title: "Update DFCite relevance: [DFCite-xxxx in DFx-xxxx]"')
    lines.append('labels: ["content: update dfcite relevance", "form input"]')
    lines.append("body:")

    # --- Explanation ---
    lines.append("  - type: markdown")
    lines.append("    attributes:")
    lines.append("      value: |")
    lines.append("        This form updates the relevance summary for a specific reference citation (DFCite)")
    lines.append("        within a technique, weakness, or mitigation. The relevance summary explains why this")
    lines.append("        reference is relevant to the item it is cited in (max 280 characters).")

    # --- Item Type ---
    lines.append("  - type: input")
    lines.append("    id: item-type")
    lines.append("    attributes:")
    lines.append("      label: Item Type")
    lines.append('      description: The type of item containing the reference ("technique", "weakness", or "mitigation").')
    lines.append("      placeholder: technique")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Item ID ---
    lines.append("  - type: input")
    lines.append("    id: item-id")
    lines.append("    attributes:")
    lines.append("      label: Item ID")
    lines.append("      description: The ID of the technique, weakness, or mitigation (e.g. DFT-1002, DFW-1001, DFM-1001).")
    lines.append("      placeholder: DFT-1002")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- DFCite ID ---
    lines.append("  - type: input")
    lines.append("    id: dfcite-id")
    lines.append("    attributes:")
    lines.append("      label: DFCite ID")
    lines.append("      description: The DFCite identifier for the reference (e.g. DFCite-1107).")
    lines.append("      placeholder: DFCite-1107")
    lines.append("    validations:")
    lines.append("      required: true")

    # --- Relevance Summary ---
    lines.append("  - type: input")
    lines.append("    id: relevance-summary")
    lines.append("    attributes:")
    lines.append("      label: Relevance Summary")
    lines.append("      description: A short summary of why this reference is relevant (max 280 characters).")
    lines.append("      placeholder: Describes the forensic analysis technique used to recover deleted files from NTFS volumes.")
    lines.append("    validations:")
    lines.append("      required: true")

    # Write output
    output_path = os.path.join(base_path, '.github', 'ISSUE_TEMPLATE', '2d_update-dfcite-relevance-form.yml')
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated: {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
