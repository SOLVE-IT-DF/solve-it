#!/usr/bin/env python3
"""Build the ontology class/property list that the Explorer's edit form uses.

The "Ontology input classes" and "Ontology output classes" fields on a technique
take full IRIs from the CASE, UCO and SOLVE-IT ontologies. Typing those by hand
is unreasonable, so the Explorer offers a searchable list instead. That list is
baked into the page at compile time by `generate_html_from_kb.py`, which reads
the JSON file this script writes.

This is deliberately a separate step from generating the page. The viewer is
rebuilt hourly; the ontologies change a few times a year. Fetching and parsing
about thirty Turtle files on every build would make the hourly job slow and
would make it fail whenever GitHub was briefly unreachable. So the output is
checked in, and refreshed by running this script when a new CASE/UCO release
is published.

Usage:
    python3 reporting_scripts/build_ontology_classes.py
    python3 reporting_scripts/build_ontology_classes.py --uco-ref 1.5.0 --case-ref 1.5.0
    python3 reporting_scripts/build_ontology_classes.py --output some/other/path.json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from rdflib import Graph, RDF, RDFS, OWL, URIRef
    from rdflib.namespace import SKOS
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    print("rdflib is required: pip install -r requirements.txt", file=sys.stderr)
    raise

UCO_REPO = "https://raw.githubusercontent.com/ucoProject/UCO"
CASE_REPO = "https://raw.githubusercontent.com/casework/CASE"
SOLVEIT_BASE = "https://raw.githubusercontent.com/SOLVE-IT-DF/solve-it-ontology/main"

DEFAULT_UCO_REF = "1.5.0"
DEFAULT_CASE_REF = "1.5.0"

# Descriptions are shown as one line of context under a search result, so the
# full rdfs:comment is more than is needed and would roughly double the size of
# the page.
MAX_DESCRIPTION = 300

# UCO modules, as paths under `ontology/` in the UCO repository.
UCO_MODULES = [
    "uco/core/core.ttl",
    "uco/observable/observable.ttl",
    "uco/action/action.ttl",
    "uco/analysis/analysis.ttl",
    "uco/configuration/configuration.ttl",
    "uco/identity/identity.ttl",
    "uco/location/location.ttl",
    "uco/marking/marking.ttl",
    "uco/pattern/pattern.ttl",
    "uco/role/role.ttl",
    "uco/time/time.ttl",
    "uco/tool/tool.ttl",
    "uco/types/types.ttl",
    "uco/victim/victim.ttl",
    "uco/vocabulary/vocabulary.ttl",
    "co/co.ttl",
]

# CASE modules, as paths under `ontology/` in the CASE repository.
CASE_MODULES = [
    "investigation/investigation.ttl",
    "vocabulary/vocabulary.ttl",
]

# SOLVE-IT ontology modules, as paths from the repository root. The knowledge
# base graph (`docs/data/solve-it-kb.ttl`) is deliberately absent: it holds
# instances of techniques and weaknesses, not classes a technique can take as
# input or produce as output.
SOLVEIT_MODULES = [
    "solve_it_core.ttl",
    "solve_it_analysis.ttl",
    "solve_it_observable.ttl",
    "solve_it_observable_acquisition.ttl",
    "solve_it_observable_search.ttl",
    "solve_it_observable_shapes.ttl",
    "solve_it_observable_timeline.ttl",
    "solve_it_sqlite.ttl",
    "solve_it_tool_profile.ttl",
    "solve_it_weakness_assessment.ttl",
]

CLASS_TYPES = {OWL.Class}
PROPERTY_TYPES = {OWL.DatatypeProperty, OWL.ObjectProperty, RDF.Property}


def source_urls(uco_ref, case_ref):
    """Return (url, source_label) pairs for every module to be fetched."""
    urls = []
    for path in UCO_MODULES:
        urls.append((f"{UCO_REPO}/{uco_ref}/ontology/{path}", "CASE/UCO"))
    for path in CASE_MODULES:
        urls.append((f"{CASE_REPO}/{case_ref}/ontology/{path}", "CASE/UCO"))
    for path in SOLVEIT_MODULES:
        urls.append((f"{SOLVEIT_BASE}/{path}", "SOLVE-IT"))
    return urls


def local_name(uri):
    """The readable tail of an IRI — the part after the last '/' or '#'."""
    return str(uri).replace("#", "/").rstrip("/").split("/")[-1]


def shorten(text):
    """Collapse whitespace and truncate to the display budget."""
    collapsed = " ".join(str(text).split())
    if len(collapsed) <= MAX_DESCRIPTION:
        return collapsed
    return collapsed[:MAX_DESCRIPTION].rstrip() + "…"


def describe(graph, subject):
    """Best available human description of a term."""
    for predicate in (RDFS.comment, SKOS.definition, RDFS.label):
        for value in graph.objects(subject, predicate):
            text = shorten(value)
            if text:
                return text
    return ""


def harvest(graph, source):
    """Extract classes and properties from one parsed graph."""
    found = {}
    for rdf_type, kind in [(t, "class") for t in CLASS_TYPES] + [(t, "property") for t in PROPERTY_TYPES]:
        for subject in graph.subjects(RDF.type, rdf_type):
            # Blank nodes are anonymous restrictions and unions, not terms a
            # contributor can name in a form.
            if not isinstance(subject, URIRef):
                continue
            uri = str(subject)
            if uri in found:
                continue
            name = local_name(uri)
            if not name:
                continue
            found[uri] = {
                "uri": uri,
                "name": name,
                "description": describe(graph, subject),
                "source": source,
                "kind": kind,
            }
    return found


def build(uco_ref, case_ref, verbose=True):
    """Fetch every module and return the merged, sorted term list."""
    terms = {}
    failures = []
    for url, source in source_urls(uco_ref, case_ref):
        graph = Graph()
        try:
            graph.parse(url, format="turtle")
        except Exception as exc:  # network, 404, or malformed Turtle
            failures.append((url, str(exc)))
            if verbose:
                print(f"  FAILED  {url} — {exc}", file=sys.stderr)
            continue
        harvested = harvest(graph, source)
        # An earlier module wins on a repeated IRI, which keeps the defining
        # module's description rather than a later import's stub.
        for uri, term in harvested.items():
            terms.setdefault(uri, term)
        if verbose:
            print(f"  ok      {url} ({len(harvested)} terms)")

    ordered = sorted(terms.values(), key=lambda t: (t["name"].lower(), t["uri"]))
    return ordered, failures


def main():
    parser = argparse.ArgumentParser(description="Build the baked-in ontology term list")
    parser.add_argument("--uco-ref", default=DEFAULT_UCO_REF, help=f"UCO release tag (default: {DEFAULT_UCO_REF})")
    parser.add_argument("--case-ref", default=DEFAULT_CASE_REF, help=f"CASE release tag (default: {DEFAULT_CASE_REF})")
    parser.add_argument("--output", default=None, help="Output JSON path (default: reporting_scripts/assets/ontology_classes.json)")
    parser.add_argument("--allow-partial", action="store_true",
                        help="Write the file even if some modules could not be fetched")
    args = parser.parse_args()

    output = Path(args.output) if args.output else Path(__file__).parent / "assets" / "ontology_classes.json"

    print(f"Fetching UCO {args.uco_ref}, CASE {args.case_ref}, SOLVE-IT main")
    terms, failures = build(args.uco_ref, args.case_ref)

    if failures and not args.allow_partial:
        print(f"\n{len(failures)} module(s) could not be fetched. Refusing to write a partial list.", file=sys.stderr)
        print("Re-run with --allow-partial to write it anyway.", file=sys.stderr)
        return 1

    payload = {
        "uco_ref": args.uco_ref,
        "case_ref": args.case_ref,
        "terms": terms,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    classes = sum(1 for t in terms if t["kind"] == "class")
    properties = len(terms) - classes
    print(f"\nWrote {output} — {len(terms)} terms ({classes} classes, {properties} properties)")
    if failures:
        print(f"WARNING: written with {len(failures)} module(s) missing", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
