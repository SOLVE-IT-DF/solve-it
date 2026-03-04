"""
SOLVE-IT Knowledge Base Combined JSON Exporter

This script generates a single combined JSON file containing all techniques,
weaknesses, mitigations, and objectives from the SOLVE-IT knowledge base.

Usage:
    python generate_combined_json_from_kb.py [-o OUTPUT_PATH]

Options:
    -o    Output file path (default: output/solve-it.json)
"""

import json
import argparse
import sys
import os
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library import KnowledgeBase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def build_combined_json(kb):
    """Build a combined dictionary of the entire knowledge base."""
    techniques = {}
    for tech_id in kb.list_techniques():
        techniques[tech_id] = kb.get_technique(tech_id)

    weaknesses = {}
    for weak_id in kb.list_weaknesses():
        weaknesses[weak_id] = kb.get_weakness(weak_id)

    mitigations = {}
    for mit_id in kb.list_mitigations():
        mitigations[mit_id] = kb.get_mitigation(mit_id)

    objectives = kb.list_objectives()

    return {
        "techniques": techniques,
        "weaknesses": weaknesses,
        "mitigations": mitigations,
        "objectives": objectives,
    }


def main():
    """Command-line entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate a combined JSON export of the SOLVE-IT knowledge base"
    )
    parser.add_argument('-o', action='store', type=str, dest='output_file',
                        default='output/solve-it.json',
                        help='Output file path (default: output/solve-it.json)')
    args = parser.parse_args()

    # Calculate the path to the solve-it directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    solve_it_root = os.path.dirname(script_dir)

    try:
        logger.info("Loading SOLVE-IT knowledge base...")
        kb = KnowledgeBase(solve_it_root, 'solve-it.json')

        logger.info("Building combined JSON...")
        combined = build_combined_json(kb)

        # Ensure output directory exists
        out_dir = os.path.dirname(args.output_file)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)

        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)

        logger.info(f"Combined JSON written to {args.output_file}")
        logger.info(
            f"  Techniques: {len(combined['techniques'])}, "
            f"Weaknesses: {len(combined['weaknesses'])}, "
            f"Mitigations: {len(combined['mitigations'])}, "
            f"Objectives: {len(combined['objectives'])}"
        )

    except Exception as e:
        logger.error(f"Error generating combined JSON: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
