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
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD

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
UCO_ACTION = Namespace("https://ontology.unifiedcyberontology.org/uco/action/")
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
    g.bind("uco-action", UCO_ACTION)
    g.bind("case-investigation", CASE_INVESTIGATION)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
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

    # Add citations
    logger.info("Adding citations to graph...")
    add_citations_to_graph(g, kb)

    # Add objectives if requested
    if include_objectives:
        logger.info("Adding objectives to graph...")
        add_objectives_to_graph(g, kb)

    logger.info(f"RDF graph built successfully with {len(g)} triples")

    return g


def build_parent_map(kb, techniques):
    """Map each sub-technique ID to the technique ID(s) that declare it.

    The KB records the relationship in one direction only: a parent lists its
    subtechniques. The metaclass model needs the reverse, because a
    sub-technique is expressed as rdfs:subClassOf its parent.
    """
    parents = {}
    for tech_id in techniques:
        tech = kb.get_technique(tech_id)
        for sub_id in tech.get('subtechniques', []):
            parents.setdefault(sub_id, []).append(tech_id)
    return parents


def add_techniques_to_graph(g, kb):
    """Add all techniques to the RDF graph.

    Each technique is emitted under the uco-action:Technique metaclass pattern
    introduced in UCO 1.5.0: it is both an instance of solveit-core:Technique
    and an owl:Class in its own right, so that a performed investigative action
    can state which technique it implements by rdf:type.

    UCO requires a Technique instance to be a subclass of uco-action:Action.
    SOLVE-IT satisfies this by placing root techniques under
    solveit-core:SolveitInvestigativeAction, which descends from
    case-investigation:InvestigativeAction and so from uco-action:Action.
    Sub-techniques inherit it through their parent.
    """
    techniques = kb.list_techniques()
    parent_map = build_parent_map(kb, techniques)
    referenced_classes = set()

    for tech_id in techniques:
        tech = kb.get_technique(tech_id)

        # Create URI for this technique (instance in data namespace)
        tech_uri = SOLVEIT_DATA[f"technique{tech_id}"]

        # Add type: an instance of the Technique metaclass, and a class itself
        g.add((tech_uri, RDF.type, SOLVEIT_CORE.Technique))
        g.add((tech_uri, RDF.type, OWL.Class))

        # Place the technique class in the action hierarchy. A sub-technique
        # sits under its parent; a root technique sits under
        # SolveitInvestigativeAction directly.
        parent_ids = parent_map.get(tech_id, [])
        if parent_ids:
            for parent_id in parent_ids:
                g.add((tech_uri, RDFS.subClassOf, SOLVEIT_DATA[f"technique{parent_id}"]))
        else:
            g.add((tech_uri, RDFS.subClassOf, SOLVEIT_CORE.SolveitInvestigativeAction))

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
        for ref in tech.get('references', []):
            if isinstance(ref, dict) and "DFCite_id" in ref:
                cite_id = ref["DFCite_id"]
                cite_uri = SOLVEIT_DATA[f"citation{cite_id}"]
                g.add((tech_uri, SOLVEIT_CORE.hasReference, cite_uri))
            else:
                g.add((tech_uri, SOLVEIT_CORE.hasReference, Literal(str(ref))))

        # Add subtechnique relationships
        for sub_id in tech.get('subtechniques', []):
            sub_uri = SOLVEIT_DATA[f"technique{sub_id}"]
            g.add((tech_uri, SOLVEIT_CORE.hasSubtechnique, sub_uri))

        # Add weakness relationships
        for weakness_id in tech.get('weaknesses', []):
            weakness_uri = SOLVEIT_DATA[f"weakness{weakness_id}"]
            g.add((tech_uri, SOLVEIT_CORE.hasPotentialWeakness, weakness_uri))

        # Add CASE input classes as IRI references, not string literals, so a
        # reasoner can follow them and a validator can check them.
        for case_class_uri in tech.get('CASE_input_classes', []):
            g.add((tech_uri, SOLVEIT_CORE.hasCASEInputClass, URIRef(case_class_uri)))
            referenced_classes.add(case_class_uri)

        # Add CASE output classes (already full URIs in the JSON)
        for case_class_uri in tech.get('CASE_output_classes', []):
            g.add((tech_uri, SOLVEIT_CORE.hasCASEOutputClass, URIRef(case_class_uri)))
            referenced_classes.add(case_class_uri)

    # Declare every referenced input/output class as an owl:Class. Without a
    # declaration, an IRI used in class position is a declaration error under
    # OWL 2 DL. This states only that the IRI names a class, which is what the
    # KB is asserting anyway; it makes no claim about the class's definition.
    for class_uri in sorted(referenced_classes):
        g.add((URIRef(class_uri), RDF.type, OWL.Class))


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

        # Add weakness class relationships
        for cls in weak.get('categories', []):
            g.add((weak_uri, SOLVEIT_CORE.hasWeaknessClass, SOLVEIT_CORE[cls]))

        # Add mitigation relationships
        for mitigation_id in weak.get('mitigations', []):
            mitigation_uri = SOLVEIT_DATA[f"mitigation{mitigation_id}"]
            g.add((weak_uri, SOLVEIT_CORE.hasPotentialMitigation, mitigation_uri))

        # Add references
        for ref in weak.get('references', []):
            if isinstance(ref, dict) and "DFCite_id" in ref:
                cite_id = ref["DFCite_id"]
                cite_uri = SOLVEIT_DATA[f"citation{cite_id}"]
                g.add((weak_uri, SOLVEIT_CORE.hasReference, cite_uri))
            else:
                g.add((weak_uri, SOLVEIT_CORE.hasReference, Literal(str(ref))))


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
        for ref in mit.get('references', []):
            if isinstance(ref, dict) and "DFCite_id" in ref:
                cite_id = ref["DFCite_id"]
                cite_uri = SOLVEIT_DATA[f"citation{cite_id}"]
                g.add((mit_uri, SOLVEIT_CORE.hasReference, cite_uri))
            else:
                g.add((mit_uri, SOLVEIT_CORE.hasReference, Literal(str(ref))))


def add_citations_to_graph(g, kb):
    """Add all citations to the RDF graph as Citation individuals."""
    for cite_id, citation in kb.citations.items():
        cite_uri = SOLVEIT_DATA[f"citation{cite_id}"]
        g.add((cite_uri, RDF.type, SOLVEIT_CORE.Citation))
        g.add((cite_uri, RDFS.label, Literal(cite_id)))
        g.add((cite_uri, SOLVEIT_CORE.citationID, Literal(cite_id)))
        g.add((cite_uri, SOLVEIT_CORE.citationPlaintext, Literal(citation.get('plaintext', ''))))
        if citation.get('bibtex'):
            g.add((cite_uri, SOLVEIT_CORE.citationBibtex, Literal(citation['bibtex'])))


def add_objectives_to_graph(g, kb):
    """Add investigation objectives to the RDF graph."""
    objectives = kb.list_objectives()

    for idx, objective in enumerate(objectives):
        obj_id = objective.get('id')
        obj_name = objective.get('name')
        obj_description = objective.get('description', '')
        sort_order = objective.get('sort_order')

        # Create URI using the real objective ID (e.g. DFO-1001), falling back to index
        uri_id = obj_id if obj_id else f"objective{idx + 1:02d}"
        obj_uri = SOLVEIT_DATA[f"objective{uri_id}"]

        # Add type
        g.add((obj_uri, RDF.type, SOLVEIT_CORE.Objective))

        # Add label
        label = f"{obj_id}: {obj_name}" if obj_id else obj_name
        g.add((obj_uri, RDFS.label, Literal(label, lang="en")))

        # Add properties
        if obj_id:
            g.add((obj_uri, SOLVEIT_CORE.objectiveID, Literal(obj_id)))
        g.add((obj_uri, SOLVEIT_CORE.objectiveName, Literal(obj_name)))

        if obj_description:
            g.add((obj_uri, SOLVEIT_CORE.objectiveDescription, Literal(obj_description)))

        if sort_order is not None:
            g.add((obj_uri, SOLVEIT_CORE.sortOrder, Literal(sort_order, datatype=XSD.integer)))

        # Link techniques to objectives
        for tech_id in objective.get('techniques', []):
            tech_uri = SOLVEIT_DATA[f"technique{tech_id}"]
            g.add((obj_uri, SOLVEIT_CORE.includesTechnique, tech_uri))


# Section layout for the Turtle output. rdflib's own serializer emits subjects
# in an order that interleaves techniques, weaknesses, mitigations and citations,
# which makes the file hard to read and hard to diff. Each entry is
# (heading, blurb, rdf:type to select on, predicate order within a subject,
#  predicate to sort subjects by — None to sort by identifier).
TTL_SECTIONS = [
    (
        'Objectives',
        'Investigation objectives, each listing the techniques that can achieve it.\n'
        '#    Ordered by solveit-core:sortOrder, which is the order objectives are\n'
        '#    worked through in an investigation, not by DFO identifier.',
        SOLVEIT_CORE.Objective,
        ['objectiveID', 'objectiveName', 'objectiveDescription', 'sortOrder',
         'includesTechnique'],
        SOLVEIT_CORE.sortOrder,
    ),
    (
        'Techniques',
        'Each technique is an instance of the solveit-core:Technique metaclass AND\n'
        '#    an owl:Class in its own right, following uco-action:Technique (UCO 1.5.0).\n'
        '#    A performed investigative action is typed with the technique class it\n'
        '#    implements. Root techniques are rdfs:subClassOf\n'
        '#    solveit-core:SolveitInvestigativeAction; sub-techniques are\n'
        '#    rdfs:subClassOf their parent technique and inherit the anchor through it.',
        SOLVEIT_CORE.Technique,
        ['techniqueID', 'techniqueName', 'techniqueDescription', 'techniqueDetails',
         'hasSynonym', 'hasExample', 'hasCASEInputClass', 'hasCASEOutputClass',
         'hasPotentialWeakness', 'hasSubtechnique', 'hasReference'],
        None,
    ),
    (
        'Weaknesses',
        'Potential problems arising from a technique, classified against the\n'
        '#    ASTM E3016-18 error categories.',
        SOLVEIT_CORE.Weakness,
        ['weaknessID', 'weaknessName', 'weaknessDescription', 'hasWeaknessClass',
         'hasPotentialMitigation', 'hasReference'],
        None,
    ),
    (
        'Mitigations',
        'Actions that prevent a weakness or reduce its impact.',
        SOLVEIT_CORE.Mitigation,
        ['mitigationID', 'mitigationName', 'mitigationDescription',
         'linksToTechnique', 'hasReference'],
        None,
    ),
    (
        'Citations',
        'Reference sources, cited by DFCite id from techniques, weaknesses\n'
        '#    and mitigations.',
        SOLVEIT_CORE.Citation,
        ['citationID', 'citationPlaintext', 'citationBibtex'],
        None,
    ),
]


def _natural_key(term, g):
    """Sort key that orders DFT-1002 before DFT-1042 before DFT-1123.

    Plain string sorting puts DFT-1123 before DFT-142, which is not what a
    reader expects. Split the local name into text and numeric runs instead.
    """
    import re
    local = str(term).rsplit('/', 1)[-1]
    return tuple(
        int(part) if part.isdigit() else part
        for part in re.split(r'(\d+)', local)
    )


def _section_key(subject, g, sort_pred):
    """Order subjects within a section.

    By identifier unless the section names a predicate to sort on, in which case
    that value leads and the identifier breaks ties. Objectives use
    solveit-core:sortOrder so the section reads in investigation order rather
    than by DFO number.
    """
    ident = _natural_key(subject, g)
    if sort_pred is None:
        return (0, ident)
    value = next(g.objects(subject, sort_pred), None)
    if value is None:
        # Anything lacking the sort value goes last, still ordered by identifier.
        return (1, ident)
    return (0, (value.toPython(),), ident)


def _emit_subject(g, subject, pred_order, nm):
    """Render one subject as a Turtle block with predicates in a chosen order."""
    lines = []
    by_pred = {}
    for p, o in g.predicate_objects(subject):
        by_pred.setdefault(p, []).append(o)

    def clause(pred_n3, objs):
        rendered = sorted(o.n3(nm) for o in objs)
        if len(rendered) == 1:
            return f"    {pred_n3} {rendered[0]}"
        joined = (',\n' + ' ' * (4 + len(pred_n3) + 1)).join(rendered)
        return f"    {pred_n3} {joined}"

    emitted = set()

    # Types first, then label, then placement in the class hierarchy.
    for pred, pred_n3 in ((RDF.type, 'a'), (RDFS.label, 'rdfs:label'),
                          (RDFS.subClassOf, 'rdfs:subClassOf')):
        if pred in by_pred:
            lines.append(clause(pred_n3, by_pred[pred]))
            emitted.add(pred)

    # Then the section's preferred order, then anything left over.
    ordered = [SOLVEIT_CORE[name] for name in pred_order]
    leftovers = sorted((p for p in by_pred if p not in emitted and p not in ordered),
                       key=str)
    for pred in ordered + leftovers:
        if pred in by_pred and pred not in emitted:
            lines.append(clause(pred.n3(nm), by_pred[pred]))
            emitted.add(pred)

    return f"{subject.n3(nm)}\n" + " ;\n".join(lines) + " .\n"


def serialize_grouped(g):
    """Serialize the graph as Turtle grouped into commented sections.

    Produces the same triples as g.serialize(format='turtle') but ordered so the
    file can be read top to bottom and diffed sensibly between builds.
    """
    nm = g.namespace_manager
    out = []

    # rdflib pre-binds a long list of well-known vocabularies (brick, csvw,
    # dcat and so on). Emit only the prefixes the graph actually uses.
    used = set()
    for triple in g:
        for term in triple:
            if isinstance(term, URIRef):
                used.add(str(term))
            elif isinstance(term, Literal) and term.datatype:
                used.add(str(term.datatype))
    out.append('\n'.join(
        f"@prefix {prefix if prefix else ''}: <{uri}> ."
        for prefix, uri in sorted(nm.namespaces(), key=lambda x: x[0])
        if any(t.startswith(str(uri)) for t in used)
    ))
    out.append('')

    counts = {t: len(set(g.subjects(RDF.type, t))) for _, _, t, _, _ in TTL_SECTIONS}
    rule = '#' * 65
    out.append(rule)
    out.append('#    SOLVE-IT Knowledge Base')
    out.append('#')
    out.append('#    Generated from the SOLVE-IT knowledge base JSON by')
    out.append('#    reporting_scripts/generate_rdf_from_kb.py. Do not edit by hand.')
    out.append('#')
    for heading, _, type_uri, _, _ in TTL_SECTIONS:
        out.append(f"#      {heading + ':':<16}{counts[type_uri]}")
    out.append(rule)
    out.append('')

    claimed = set()
    for heading, blurb, type_uri, pred_order, sort_pred in TTL_SECTIONS:
        subjects = sorted(
            set(g.subjects(RDF.type, type_uri)),
            key=lambda s: _section_key(s, g, sort_pred),
        )
        claimed.update(subjects)
        out.append(rule)
        out.append(f"#    {heading} ({len(subjects)})")
        out.append('#')
        out.append(f"#    {blurb}")
        out.append(rule)
        out.append('')
        for s in subjects:
            out.append(_emit_subject(g, s, pred_order, nm))

    # Declaration-only stubs for the CASE/UCO classes referenced as technique
    # inputs and outputs. Without these an IRI in class position is a
    # declaration error under OWL 2 DL.
    remaining = sorted((s for s in set(g.subjects()) if s not in claimed),
                       key=lambda s: _natural_key(s, g))
    if remaining:
        out.append(rule)
        out.append(f"#    Referenced CASE/UCO classes ({len(remaining)})")
        out.append('#')
        out.append('#    Declaration only. These name classes defined in CASE/UCO or in')
        out.append('#    the SOLVE-IT observable modules, referenced above as technique')
        out.append('#    input and output classes. No definition is asserted here.')
        out.append(rule)
        out.append('')
        for s in remaining:
            out.append(_emit_subject(g, s, [], nm))

    return '\n'.join(out)


def save_graph(g, output_dir, format_type='both'):
    """
    Save the RDF graph to file(s).

    Args:
        g: rdflib.Graph to save
        output_dir: Directory path to write files
        format_type: 'ttl', 'jsonld', or 'both'
    """
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    if format_type in ['ttl', 'both']:
        ttl_file = output_path / 'solve-it-kb.ttl'
        logger.info(f"Writing Turtle output to {ttl_file}")
        # Grouped into commented sections rather than rdflib's own subject order,
        # which interleaves techniques, weaknesses, mitigations and citations.
        ttl_output = serialize_grouped(g)
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write(ttl_output)
        logger.info(f"Turtle file written successfully: {ttl_file}")

    if format_type in ['jsonld', 'both']:
        jsonld_file = output_path / 'solve-it-kb.jsonld'
        logger.info(f"Writing JSON-LD output to {jsonld_file}")
        # Serialize to string, then sort for deterministic output
        import json
        jsonld_str = g.serialize(format='json-ld')
        jsonld_data = json.loads(jsonld_str)
        # Sort @graph entries by @id for stable diffs
        if isinstance(jsonld_data, list):
            jsonld_data.sort(key=lambda x: x.get('@id', ''))
        elif isinstance(jsonld_data, dict) and '@graph' in jsonld_data:
            jsonld_data['@graph'].sort(key=lambda x: x.get('@id', ''))
        with open(jsonld_file, 'w', encoding='utf-8') as f:
            json.dump(jsonld_data, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write('\n')
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
