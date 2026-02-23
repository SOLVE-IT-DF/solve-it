"""
SOLVE-IT Ontology Lookup Utility

Loads SOLVE-IT and (optionally) CASE/UCO ontology files via rdflib to provide
class descriptions for enriching knowledge base outputs.

Usage:
    # From a local clone
    lookup = OntologyLookup(solve_it_ontology_path="/path/to/solve-it-ontology")

    # From GitHub (no local clone needed)
    lookup = OntologyLookup(solve_it_ontology_url=SOLVEIT_ONTOLOGY_DEFAULT_URL)

    details = lookup.describe_class("https://ontology.solveit-df.org/solveit/observable/DeviceSet")
    markdown = lookup.format_markdown_details("https://ontology.solveit-df.org/solveit/observable/DeviceSet")
"""

import logging
from pathlib import Path

from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL

SH = Namespace("http://www.w3.org/ns/shacl#")

logger = logging.getLogger(__name__)

# Known namespace prefixes for display
NAMESPACE_PREFIXES = {
    "https://ontology.solveit-df.org/solveit/observable/": "solveit-observable",
    "https://ontology.solveit-df.org/solveit/core/": "solveit-core",
    "https://ontology.solveit-df.org/solveit/analysis/": "solveit-analysis",
    "https://ontology.unifiedcyberontology.org/uco/core/": "uco-core",
    "https://ontology.unifiedcyberontology.org/uco/observable/": "uco-observable",
    "https://ontology.unifiedcyberontology.org/uco/analysis/": "uco-analysis",
    "https://ontology.caseontology.org/case/investigation/": "case-investigation",
    "https://cacontology.projectvic.org/forensics#": "projectvic",
    "http://www.w3.org/2002/07/owl#": "owl",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
    "http://www.w3.org/2001/XMLSchema#": "xsd",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
}

# SOLVE-IT ontology TTL files to load (relative to ontology repo root or base URL)
SOLVEIT_ONTOLOGY_FILES = [
    "solve_it_core.ttl",
    "solve_it_observable.ttl",
    "solve_it_observable_acquisition.ttl",
    "solve_it_observable_timeline.ttl",
    "solve_it_observable_search.ttl",
    "solve_it_analysis.ttl",
    "solve_it_observable_shapes.ttl",
]

# Default GitHub raw URL base for SOLVE-IT ontology
SOLVEIT_ONTOLOGY_DEFAULT_URL = (
    "https://raw.githubusercontent.com/SOLVE-IT-DF/solve-it-ontology/main/"
)

# UCO/CASE ontology module URLs for 1.4.0
UCO_CASE_MODULES = [
    "https://raw.githubusercontent.com/ucoProject/UCO/1.4.0/ontology/uco/core/core.ttl",
    "https://raw.githubusercontent.com/ucoProject/UCO/1.4.0/ontology/uco/observable/observable.ttl",
    "https://raw.githubusercontent.com/ucoProject/UCO/1.4.0/ontology/uco/analysis/analysis.ttl",
]


class OntologyLookup:
    """Loads ontology files and provides class description lookups."""

    def __init__(self, solve_it_ontology_path=None, solve_it_ontology_url=None,
                 load_case_uco=False, case_uco_cache_dir=None):
        """
        Initialise the ontology lookup.

        Args:
            solve_it_ontology_path: Path to the solve-it-ontology repository root (local).
            solve_it_ontology_url: Base URL for SOLVE-IT ontology TTL files (remote).
                                    Use SOLVEIT_ONTOLOGY_DEFAULT_URL for GitHub main branch.
                                    If both path and url are provided, path takes priority.
            load_case_uco: Whether to attempt loading CASE/UCO ontology modules.
            case_uco_cache_dir: Directory to cache downloaded TTL files.
                                Defaults to ~/.cache/solveit-ontology/
        """
        self.graph = Graph()
        self._loaded_sources = []

        # Determine cache directory
        if case_uco_cache_dir:
            self._cache_dir = Path(case_uco_cache_dir)
        else:
            self._cache_dir = Path.home() / ".cache" / "solveit-ontology"

        # Load SOLVE-IT ontology (local path takes priority over URL)
        if solve_it_ontology_path:
            self._load_solveit_from_path(Path(solve_it_ontology_path))
        elif solve_it_ontology_url:
            self._load_solveit_from_url(solve_it_ontology_url)

        if load_case_uco:
            self._load_remote_modules(UCO_CASE_MODULES)

        logger.info(f"Ontology loaded: {len(self.graph)} triples from {len(self._loaded_sources)} sources")

    def _load_solveit_from_path(self, ontology_path):
        """Load SOLVE-IT ontology TTL files from a local directory."""
        for ttl_file in SOLVEIT_ONTOLOGY_FILES:
            filepath = ontology_path / ttl_file
            if filepath.exists():
                try:
                    self.graph.parse(str(filepath), format="turtle")
                    self._loaded_sources.append(str(filepath))
                    logger.debug(f"Loaded: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to parse {filepath}: {e}")
            else:
                logger.debug(f"Ontology file not found: {filepath}")

    def _load_solveit_from_url(self, base_url):
        """Load SOLVE-IT ontology TTL files from a remote URL base."""
        # Ensure trailing slash
        if not base_url.endswith("/"):
            base_url += "/"
        urls = [base_url + f for f in SOLVEIT_ONTOLOGY_FILES]
        self._load_remote_modules(urls)

    def _load_remote_modules(self, urls):
        """Load TTL files from remote URLs, using a local cache."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        for url in urls:
            filename = url.split("/")[-1]
            cached_file = self._cache_dir / filename

            # Try loading from cache first
            if cached_file.exists():
                try:
                    self.graph.parse(str(cached_file), format="turtle")
                    self._loaded_sources.append(f"cached:{cached_file}")
                    logger.debug(f"Loaded from cache: {cached_file}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to parse cached file {cached_file}: {e}")

            # Download, cache, then load from cache
            try:
                self._download_file(url, cached_file)
                self.graph.parse(str(cached_file), format="turtle")
                self._loaded_sources.append(url)
                logger.debug(f"Loaded from URL: {url}")
            except Exception as e:
                logger.warning(f"Failed to load remote module {url}: {e}")

    @staticmethod
    def _download_file(url, dest):
        """Download a file, using requests (handles SSL properly) or falling back to urllib."""
        try:
            import requests
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        except ImportError:
            import urllib.request
            urllib.request.urlretrieve(url, str(dest))

    def clear_cache(self):
        """Remove all cached ontology files."""
        if self._cache_dir.exists():
            import shutil
            shutil.rmtree(self._cache_dir)
            logger.info(f"Cleared ontology cache: {self._cache_dir}")

    def shorten_uri(self, uri):
        """Convert a full URI to a prefixed short form for display."""
        uri_str = str(uri)
        for namespace, prefix in NAMESPACE_PREFIXES.items():
            if uri_str.startswith(namespace):
                local_name = uri_str[len(namespace):]
                return f"{prefix}:{local_name}"
        # If the URI contains a # fragment, use that
        if "#" in uri_str:
            return uri_str.split("#")[-1]
        # Otherwise use the last path segment
        return uri_str.split("/")[-1]

    def describe_class(self, class_uri):
        """
        Get a description of a class from the loaded ontology.

        Args:
            class_uri: Full URI string of the class to describe.

        Returns:
            dict with keys:
                - superclasses: list of short-form superclass names
                - object_properties: list of dicts with 'name', 'range' (short forms)
                - data_properties: list of dicts with 'name', 'range' (short forms)
                - comment: rdfs:comment string if available
                - found: bool indicating whether the class was found in the ontology
        """
        uri = URIRef(class_uri)
        result = {
            "superclasses": [],
            "object_properties": [],
            "data_properties": [],
            "comment": None,
            "found": False,
        }

        # Check if the class exists in the ontology
        is_class = (uri, RDF.type, OWL.Class) in self.graph
        has_any_triple = any(self.graph.triples((uri, None, None)))
        if not is_class and not has_any_triple:
            return result

        result["found"] = True

        # Get rdfs:comment
        for comment in self.graph.objects(uri, RDFS.comment):
            result["comment"] = str(comment)
            break

        # Get superclasses (skip OWL restrictions and blank nodes)
        for superclass in self.graph.objects(uri, RDFS.subClassOf):
            if isinstance(superclass, URIRef):
                result["superclasses"].append(self.shorten_uri(superclass))

        # Get object properties where this class is the domain
        for prop in self.graph.subjects(RDFS.domain, uri):
            if (prop, RDF.type, OWL.ObjectProperty) in self.graph:
                ranges = []
                for range_class in self.graph.objects(prop, RDFS.range):
                    if isinstance(range_class, URIRef):
                        ranges.append(self.shorten_uri(range_class))
                result["object_properties"].append({
                    "name": self.shorten_uri(prop),
                    "range": ", ".join(ranges) if ranges else "unspecified",
                })

        # Get data properties where this class is the domain
        for prop in self.graph.subjects(RDFS.domain, uri):
            if (prop, RDF.type, OWL.DatatypeProperty) in self.graph:
                ranges = []
                for range_type in self.graph.objects(prop, RDFS.range):
                    if isinstance(range_type, URIRef):
                        ranges.append(self.shorten_uri(range_type))
                result["data_properties"].append({
                    "name": self.shorten_uri(prop),
                    "range": ", ".join(ranges) if ranges else "unspecified",
                })

        # Look for UCO-style facet properties (e.g. DeviceFacet for Device)
        facet_props = self._get_facet_properties(class_uri)
        if facet_props:
            result["data_properties"].extend(facet_props["data_properties"])
            result["object_properties"].extend(facet_props["object_properties"])

        return result

    def _get_facet_properties(self, class_uri):
        """
        Look up properties from a corresponding UCO Facet class via SHACL shapes.

        UCO classes like Device have a corresponding DeviceFacet that holds
        the actual properties (manufacturer, model, serialNumber, etc.)
        defined as sh:property constraints.
        """
        uri_str = str(class_uri)

        # Derive the facet class URI by appending "Facet" to the class name
        # e.g. .../observable/Device -> .../observable/DeviceFacet
        facet_uri = URIRef(uri_str + "Facet")

        # Check if this facet class exists
        if not any(self.graph.triples((facet_uri, None, None))):
            return None

        result = {"data_properties": [], "object_properties": []}

        # Parse sh:property constraints from the facet's SHACL shape
        for prop_node in self.graph.objects(facet_uri, SH.property):
            # Get the property path (sh:path)
            path = None
            for p in self.graph.objects(prop_node, SH.path):
                if isinstance(p, URIRef):
                    path = p
                    break

            if path is None:
                continue

            prop_name = self.shorten_uri(path)

            # Determine if it's a data property (sh:datatype) or object property (sh:class)
            datatype = None
            for dt in self.graph.objects(prop_node, SH.datatype):
                datatype = self.shorten_uri(dt)
                break

            obj_class = None
            for oc in self.graph.objects(prop_node, SH["class"]):
                obj_class = self.shorten_uri(oc)
                break

            if obj_class:
                result["object_properties"].append({
                    "name": prop_name,
                    "range": obj_class,
                })
            else:
                result["data_properties"].append({
                    "name": prop_name,
                    "range": datatype if datatype else "unspecified",
                })

        return result

    def format_markdown_details(self, class_uri):
        """
        Format ontology information about a class as a collapsible markdown block.

        Shows only containment/composition relationships and data properties.
        Omits superclasses and descriptions to keep the output concise.

        Args:
            class_uri: Full URI string of the class.

        Returns:
            String of markdown to append after the class list item,
            or empty string if no relevant properties are available.
        """
        desc = self.describe_class(class_uri)

        if not desc["found"]:
            return ""

        has_content = desc["object_properties"] or desc["data_properties"]
        if not has_content:
            return ""

        lines = []
        lines.append("    <details>")
        lines.append("    <summary>Properties</summary>")
        lines.append("    <ul>")

        for prop in desc["object_properties"]:
            lines.append(f"    <li>{prop['name']} &rarr; {prop['range']}</li>")

        for prop in desc["data_properties"]:
            lines.append(f"    <li>{prop['name']} ({prop['range']})</li>")

        lines.append("    </ul>")
        lines.append("    </details>")

        return "\n".join(lines)
