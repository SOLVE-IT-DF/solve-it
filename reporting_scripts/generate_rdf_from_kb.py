"""
SOLVE-IT Knowledge Base RDF Exporter

This script generates RDF representations (Turtle and JSON-LD) of the SOLVE-IT knowledge base.

The script loads the knowledge base and converts it to RDF triples using the SOLVE-IT ontology
(https://ontology.solveit-df.org/) and CASE/UCO ontology references.

Usage:
    python generate_rdf_from_kb.py [--output-dir OUTPUT_DIR] [--format FORMAT]

Options:
    --output-dir    Directory to write output files (default: ../output/)
    --format        Output format: ttl, jsonld, or both (default: both)
    --objective     Objective mapping file to use (default: solve-it.json)

Example:
    python generate_rdf_from_kb.py --output-dir ../output/ --format both
"""

import argparse
import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library import KnowledgeBase
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# Define namespaces
# Vocabulary/Schema namespaces
SOLVEIT_CORE = Namespace("https://ontology.solveit-df.org/solveit/core/")
SOLVEIT_OBSERVABLE = Namespace("https://ontology.solveit-df.org/solveit/observable/")
SOLVEIT_ANALYSIS = Namespace("https://ontology.solveit-df.org/solveit/analysis/")
# Instance data namespace
SOLVEIT_DATA = Namespace("https://ontology.solveit-df.org/solveit/data/")
# External ontologies
UCO_CORE = Namespace("https://ontology.unifiedcyberontology.org/uco/core/")
UCO_OBSERVABLE = Namespace("https://ontology.unifiedcyberontology.org/uco/observable/")
CASE_INVESTIGATION = Namespace("https://ontology.caseontology.org/case/investigation/")


def create_rdf_graph(kb, include_objectives=True):
    """
    Creates an RDF graph from the SOLVE-IT knowledge base.

    Args:
        kb: KnowledgeBase instance
        include_objectives: Whether to include objective mappings (default: True)

    Returns:
        rdflib.Graph: The populated RDF graph
    """
    g = Graph()

    # Bind namespaces for cleaner output
    g.bind("", SOLVEIT_DATA)  # Default namespace for instances
    g.bind("solveit-core", SOLVEIT_CORE)
    g.bind("solveit-observable", SOLVEIT_OBSERVABLE)
    g.bind("solveit-analysis", SOLVEIT_ANALYSIS)
    g.bind("uco-core", UCO_CORE)
    g.bind("uco-observable", UCO_OBSERVABLE)
    g.bind("case-investigation", CASE_INVESTIGATION)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    logger.info("Building RDF graph from knowledge base...")

    # Add techniques
    logger.info("Adding techniques to graph...")
    add_techniques_to_graph(g, kb)

    # Add weaknesses
    logger.info("Adding weaknesses to graph...")
    add_weaknesses_to_graph(g, kb)

    # Add mitigations
    logger.info("Adding mitigations to graph...")
    add_mitigations_to_graph(g, kb)

    # Add objectives if requested
    if include_objectives:
        logger.info("Adding objectives to graph...")
        add_objectives_to_graph(g, kb)

    logger.info(f"RDF graph built successfully with {len(g)} triples")

    return g


def add_techniques_to_graph(g, kb):
    """Add all techniques to the RDF graph."""
    techniques = kb.list_techniques()

    for tech_id in techniques:
        tech = kb.get_technique(tech_id)

        # Create URI for this technique (instance in data namespace)
        tech_uri = SOLVEIT_DATA[f"technique{tech_id}"]

        # Add type
        g.add((tech_uri, RDF.type, SOLVEIT_CORE.Technique))

        # Add label
        g.add((tech_uri, RDFS.label, Literal(f"{tech_id}: {tech['name']}", lang="en")))

        # Add basic properties
        g.add((tech_uri, SOLVEIT_CORE.techniqueID, Literal(tech_id)))
        g.add((tech_uri, SOLVEIT_CORE.techniqueName, Literal(tech['name'])))

        if tech.get('description'):
            g.add((tech_uri, SOLVEIT_CORE.techniqueDescription, Literal(tech['description'])))

        if tech.get('details'):
            g.add((tech_uri, SOLVEIT_CORE.techniqueDetails, Literal(tech['details'])))

        # Add synonyms
        for synonym in tech.get('synonyms', []):
            g.add((tech_uri, SOLVEIT_CORE.hasSynonym, Literal(synonym)))

        # Add examples
        for example in tech.get('examples', []):
            g.add((tech_uri, SOLVEIT_CORE.hasExample, Literal(example)))

        # Add references
        for reference in tech.get('references', []):
            g.add((tech_uri, SOLVEIT_CORE.hasReference, Literal(reference)))

        # Add subtechnique relationships
        for sub_id in tech.get('subtechniques', []):
            sub_uri = SOLVEIT_DATA[f"technique{sub_id}"]
            g.add((tech_uri, SOLVEIT_CORE.hasSubtechnique, sub_uri))

        # Add weakness relationships
        for weakness_id in tech.get('weaknesses', []):
            weakness_uri = SOLVEIT_DATA[f"weakness{weakness_id}"]
            g.add((tech_uri, SOLVEIT_CORE.hasPotentialWeakness, weakness_uri))

        # Add CASE output classes (as xsd:anyURI typed literals)
        for case_class_uri in tech.get('CASE_output_classes', []):
            # CASE_output_classes are already full URIs in the JSON
            g.add((tech_uri, SOLVEIT_CORE.hasCASEOutputClass, Literal(case_class_uri, datatype=XSD.anyURI)))


def add_weaknesses_to_graph(g, kb):
    """Add all weaknesses to the RDF graph."""
    weaknesses = kb.list_weaknesses()

    for weak_id in weaknesses:
        weak = kb.get_weakness(weak_id)

        # Create URI for this weakness (instance in data namespace)
        weak_uri = SOLVEIT_DATA[f"weakness{weak_id}"]

        # Add type
        g.add((weak_uri, RDF.type, SOLVEIT_CORE.Weakness))

        # Add label
        g.add((weak_uri, RDFS.label, Literal(f"{weak_id}: {weak['name']}", lang="en")))

        # Add basic properties
        g.add((weak_uri, SOLVEIT_CORE.weaknessID, Literal(weak_id)))
        g.add((weak_uri, SOLVEIT_CORE.weaknessName, Literal(weak['name'])))

        # Add description if present
        if weak.get('description'):
            g.add((weak_uri, SOLVEIT_CORE.weaknessDescription, Literal(weak['description'])))

        # Add ALL error category flags explicitly (true or false)
        # This follows the pattern in the ontology examples
        g.add((weak_uri, SOLVEIT_CORE.mayResultInINCOMP,
               Literal(bool(weak.get('INCOMP')), datatype=XSD.boolean)))

        g.add((weak_uri, SOLVEIT_CORE.mayResultInINAC_EX,
               Literal(bool(weak.get('INAC_EX')), datatype=XSD.boolean)))

        g.add((weak_uri, SOLVEIT_CORE.mayResultInINAC_AS,
               Literal(bool(weak.get('INAC_AS')), datatype=XSD.boolean)))

        g.add((weak_uri, SOLVEIT_CORE.mayResultInINAC_ALT,
               Literal(bool(weak.get('INAC_ALT')), datatype=XSD.boolean)))

        g.add((weak_uri, SOLVEIT_CORE.mayResultInINAC_COR,
               Literal(bool(weak.get('INAC_COR')), datatype=XSD.boolean)))

        g.add((weak_uri, SOLVEIT_CORE.mayResultInMISINT,
               Literal(bool(weak.get('MISINT')), datatype=XSD.boolean)))

        # Add mitigation relationships
        for mitigation_id in weak.get('mitigations', []):
            mitigation_uri = SOLVEIT_DATA[f"mitigation{mitigation_id}"]
            g.add((weak_uri, SOLVEIT_CORE.hasPotentialMitigation, mitigation_uri))

        # Add references
        for reference in weak.get('references', []):
            g.add((weak_uri, SOLVEIT_CORE.hasReference, Literal(reference)))


def add_mitigations_to_graph(g, kb):
    """Add all mitigations to the RDF graph."""
    mitigations = kb.list_mitigations()

    for mit_id in mitigations:
        mit = kb.get_mitigation(mit_id)

        # Create URI for this mitigation (instance in data namespace)
        mit_uri = SOLVEIT_DATA[f"mitigation{mit_id}"]

        # Add type
        g.add((mit_uri, RDF.type, SOLVEIT_CORE.Mitigation))

        # Add label
        g.add((mit_uri, RDFS.label, Literal(f"{mit_id}: {mit['name']}", lang="en")))

        # Add basic properties
        g.add((mit_uri, SOLVEIT_CORE.mitigationID, Literal(mit_id)))
        g.add((mit_uri, SOLVEIT_CORE.mitigationName, Literal(mit['name'])))

        # Add description if present
        if mit.get('description'):
            g.add((mit_uri, SOLVEIT_CORE.mitigationDescription, Literal(mit['description'])))

        # Add technique link if present
        if mit.get('technique'):
            technique_uri = SOLVEIT_DATA[f"technique{mit['technique']}"]
            g.add((mit_uri, SOLVEIT_CORE.linksToTechnique, technique_uri))

        # Add references
        for reference in mit.get('references', []):
            g.add((mit_uri, SOLVEIT_CORE.hasReference, Literal(reference)))


def add_objectives_to_graph(g, kb):
    """Add investigation objectives to the RDF graph."""
    objectives = kb.list_objectives()

    for idx, objective in enumerate(objectives, 1):
        obj_name = objective.get('name')
        obj_description = objective.get('description', '')

        # Create URI for this objective (using numeric ID to avoid special chars)
        obj_uri = SOLVEIT_DATA[f"objective{idx:02d}"]

        # Add type
        g.add((obj_uri, RDF.type, SOLVEIT_CORE.Objective))

        # Add label
        g.add((obj_uri, RDFS.label, Literal(obj_name, lang="en")))

        # Add properties
        g.add((obj_uri, SOLVEIT_CORE.objectiveName, Literal(obj_name)))

        if obj_description:
            g.add((obj_uri, SOLVEIT_CORE.objectiveDescription, Literal(obj_description)))

        # Link techniques to objectives
        for tech_id in objective.get('techniques', []):
            tech_uri = SOLVEIT_DATA[f"technique{tech_id}"]
            g.add((obj_uri, SOLVEIT_CORE.includesTechnique, tech_uri))


def save_graph(g, output_dir, format_type='both'):
    """
    Save the RDF graph to file(s).

    Args:
        g: rdflib.Graph to save
        output_dir: Directory path to write files
        format_type: 'ttl', 'jsonld', or 'both'
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if format_type in ['ttl', 'both']:
        ttl_file = output_path / 'solve-it-kb.ttl'
        logger.info(f"Writing Turtle output to {ttl_file}")
        g.serialize(destination=str(ttl_file), format='turtle')
        logger.info(f"Turtle file written successfully: {ttl_file}")

    if format_type in ['jsonld', 'both']:
        jsonld_file = output_path / 'solve-it-kb.jsonld'
        logger.info(f"Writing JSON-LD output to {jsonld_file}")
        g.serialize(destination=str(jsonld_file), format='json-ld')
        logger.info(f"JSON-LD file written successfully: {jsonld_file}")


def main():
    """Main function to parse arguments and generate RDF output."""
    parser = argparse.ArgumentParser(
        description='Generate RDF (Turtle and/or JSON-LD) from SOLVE-IT knowledge base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--output-dir',
        default='../output/',
        help='Directory to write output files (default: ../output/)'
    )

    parser.add_argument(
        '--format',
        choices=['ttl', 'jsonld', 'both'],
        default='both',
        help='Output format: ttl (Turtle), jsonld (JSON-LD), or both (default: both)'
    )

    parser.add_argument(
        '--objective',
        default='solve-it.json',
        help='Objective mapping file to use (default: solve-it.json)'
    )

    parser.add_argument(
        '--no-objectives',
        action='store_true',
        help='Exclude objective mappings from output'
    )

    args = parser.parse_args()

    try:
        # Load the knowledge base
        logger.info(f"Loading SOLVE-IT knowledge base with objective mapping: {args.objective}")
        base_path = os.path.join(os.path.dirname(__file__), '..')
        kb = KnowledgeBase(
            base_path=base_path,
            mapping_file=args.objective
        )

        # Create RDF graph
        g = create_rdf_graph(kb, include_objectives=not args.no_objectives)

        # Save to file(s)
        save_graph(g, args.output_dir, args.format)

        logger.info("RDF generation completed successfully!")

    except Exception as e:
        logger.error(f"Error generating RDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
