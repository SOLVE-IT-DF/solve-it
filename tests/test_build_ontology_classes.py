"""Tests for reporting_scripts/build_ontology_classes.py.

The script's network fetch is not exercised here; the graphs are built in
memory, which is enough to cover extraction, description choice, truncation,
duplicate handling and the failure path.
"""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
import build_ontology_classes as boc
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, BNode, URIRef
from rdflib.namespace import SKOS

EX = Namespace("https://example.org/ont/")


def graph_with(*triples):
    g = Graph()
    for t in triples:
        g.add(t)
    return g


class TestHarvest(unittest.TestCase):

    def test_extracts_classes_and_properties_with_kind(self):
        g = graph_with(
            (EX.File, RDF.type, OWL.Class),
            (EX.fileName, RDF.type, OWL.DatatypeProperty),
            (EX.hasPart, RDF.type, OWL.ObjectProperty),
        )
        found = boc.harvest(g, "CASE/UCO")
        self.assertEqual(found[str(EX.File)]["kind"], "class")
        self.assertEqual(found[str(EX.fileName)]["kind"], "property")
        self.assertEqual(found[str(EX.hasPart)]["kind"], "property")
        self.assertTrue(all(t["source"] == "CASE/UCO" for t in found.values()))

    def test_skips_blank_nodes(self):
        # Anonymous restrictions and unions are typed owl:Class too, but a
        # contributor cannot name them in a form.
        g = graph_with((BNode(), RDF.type, OWL.Class), (EX.File, RDF.type, OWL.Class))
        self.assertEqual(list(boc.harvest(g, "CASE/UCO")), [str(EX.File)])

    def test_name_is_the_local_part_of_the_iri(self):
        g = graph_with((EX.File, RDF.type, OWL.Class))
        self.assertEqual(boc.harvest(g, "CASE/UCO")[str(EX.File)]["name"], "File")

    def test_hash_iris_take_the_fragment_as_the_name(self):
        self.assertEqual(boc.local_name("https://example.org/ont#ExpertReport"), "ExpertReport")


class TestDescribe(unittest.TestCase):

    def test_prefers_comment_then_definition_then_label(self):
        g = graph_with(
            (EX.A, RDFS.comment, Literal("A comment")),
            (EX.A, SKOS.definition, Literal("A definition")),
            (EX.B, SKOS.definition, Literal("B definition")),
            (EX.B, RDFS.label, Literal("B label")),
            (EX.C, RDFS.label, Literal("C label")),
        )
        self.assertEqual(boc.describe(g, EX.A), "A comment")
        self.assertEqual(boc.describe(g, EX.B), "B definition")
        self.assertEqual(boc.describe(g, EX.C), "C label")

    def test_no_description_gives_empty_string(self):
        self.assertEqual(boc.describe(Graph(), EX.A), "")


class TestShorten(unittest.TestCase):

    def test_collapses_whitespace(self):
        self.assertEqual(boc.shorten("a   b\n\tc"), "a b c")

    def test_truncates_over_the_budget_with_an_ellipsis(self):
        text = "x" * (boc.MAX_DESCRIPTION + 50)
        out = boc.shorten(text)
        self.assertTrue(out.endswith("…"))
        self.assertEqual(len(out), boc.MAX_DESCRIPTION + 1)

    def test_leaves_short_text_alone(self):
        self.assertEqual(boc.shorten("short"), "short")


class TestBuild(unittest.TestCase):

    def _run(self, graphs_by_url, fail=()):
        """Drive build() with in-memory graphs instead of fetched Turtle."""
        def fake_parse(self, source=None, format=None, **kw):
            if source in fail:
                raise IOError("simulated fetch failure")
            for t in graphs_by_url.get(source, Graph()):
                self.add(t)
            return self
        with mock.patch.object(Graph, "parse", fake_parse):
            return boc.build("1.5.0", "1.5.0", verbose=False)

    def test_first_module_wins_on_a_repeated_iri(self):
        urls = [u for u, _ in boc.source_urls("1.5.0", "1.5.0")]
        first, second = urls[0], urls[1]
        graphs = {
            first: graph_with((EX.File, RDF.type, OWL.Class), (EX.File, RDFS.comment, Literal("defining module"))),
            second: graph_with((EX.File, RDF.type, OWL.Class), (EX.File, RDFS.comment, Literal("later stub"))),
        }
        terms, failures = self._run(graphs)
        self.assertEqual(failures, [])
        self.assertEqual([t["description"] for t in terms if t["name"] == "File"], ["defining module"])

    def test_solveit_modules_are_labelled_as_such(self):
        urls = boc.source_urls("1.5.0", "1.5.0")
        solveit_url = next(u for u, src in urls if src == "SOLVE-IT")
        terms, _ = self._run({solveit_url: graph_with((EX.Bitstream, RDF.type, OWL.Class))})
        self.assertEqual([t["source"] for t in terms], ["SOLVE-IT"])

    def test_output_is_sorted_by_name(self):
        url = boc.source_urls("1.5.0", "1.5.0")[0][0]
        g = graph_with((EX.Zeta, RDF.type, OWL.Class), (EX.alpha, RDF.type, OWL.Class), (EX.Mid, RDF.type, OWL.Class))
        terms, _ = self._run({url: g})
        self.assertEqual([t["name"] for t in terms], ["alpha", "Mid", "Zeta"])

    def test_a_failed_module_is_reported_and_the_rest_still_harvested(self):
        urls = [u for u, _ in boc.source_urls("1.5.0", "1.5.0")]
        terms, failures = self._run({urls[1]: graph_with((EX.File, RDF.type, OWL.Class))}, fail=(urls[0],))
        self.assertEqual([u for u, _ in failures], [urls[0]])
        self.assertEqual([t["name"] for t in terms], ["File"])


class TestMain(unittest.TestCase):

    def test_refuses_to_write_a_partial_list_without_the_flag(self):
        with mock.patch.object(boc, "build", return_value=([], [("u", "err")])):
            with mock.patch.object(sys, "argv", ["build_ontology_classes.py", "--output", os.devnull]):
                self.assertEqual(boc.main(), 1)

    def test_writes_the_payload_shape_the_generator_reads(self):
        import tempfile
        term = {"uri": "https://example.org/ont/File", "name": "File", "description": "", "source": "CASE/UCO", "kind": "class"}
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "ontology_classes.json")
            with mock.patch.object(boc, "build", return_value=([term], [])):
                with mock.patch.object(sys, "argv", ["build_ontology_classes.py", "--output", out]):
                    self.assertEqual(boc.main(), 0)
            payload = json.load(open(out))
        self.assertEqual(payload["terms"], [term])
        self.assertEqual(payload["uco_ref"], boc.DEFAULT_UCO_REF)


if __name__ == '__main__':
    unittest.main()
