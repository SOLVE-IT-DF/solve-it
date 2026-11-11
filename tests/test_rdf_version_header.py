"""
The RDF export states which version of the knowledge base it was built from,
as an ontology header on the data namespace IRI (data/solveit_version.json is
the source). The header must come first in both serialisations and must not
be filed among the declaration-only CASE/UCO class stubs.
"""

import json
import os
import sys
import unittest
from unittest import mock

from rdflib import Literal, URIRef, RDF, OWL, XSD

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
from solve_it_library import KnowledgeBase  # noqa: E402
import generate_rdf_from_kb as gen  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')


class TestRdfVersionHeader(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase(ROOT, 'solve-it.json')
        with open(os.path.join(ROOT, 'data', 'solveit_version.json'), encoding='utf-8') as f:
            cls.info = json.load(f)
        cls.g = gen.create_rdf_graph(cls.kb)

    def test_header_states_version_time_and_commit(self):
        h = gen.KB_HEADER
        self.assertIn((h, RDF.type, OWL.Ontology), self.g)
        self.assertIn((h, OWL.versionInfo, Literal(self.info['version'])), self.g)
        modified = list(self.g.objects(h, gen.DCTERMS.modified))
        self.assertEqual([str(m) for m in modified], [self.info['committed_at']])
        self.assertIn((h, gen.DCTERMS.source,
                       URIRef('https://github.com/SOLVE-IT-DF/solve-it/commit/' + self.info['commit'])), self.g)

    def test_timestamp_text_matches_the_version_file(self):
        ttl = gen.serialize_grouped(self.g)
        self.assertIn(f'dcterms:modified "{self.info["committed_at"]}"^^xsd:dateTime', ttl)

    def test_header_comes_first_in_turtle_and_not_among_class_stubs(self):
        ttl = gen.serialize_grouped(self.g)
        header_at = ttl.index('#    Knowledge base version')
        self.assertLess(header_at, ttl.index('#    Objectives ('))
        stubs = ttl.split('#    Referenced CASE/UCO classes', 1)
        if len(stubs) == 2:
            self.assertNotIn('a owl:Ontology', stubs[1])

    def test_header_comes_first_in_jsonld(self):
        order = gen.jsonld_node_order(self.g)
        self.assertEqual(min(order, key=order.get), str(gen.KB_HEADER))

    def test_no_version_file_means_no_header(self):
        with mock.patch.object(self.kb, 'get_version_info', return_value=None):
            g = gen.create_rdf_graph(self.kb)
        self.assertNotIn((gen.KB_HEADER, RDF.type, OWL.Ontology), g)
        self.assertNotIn('Knowledge base version', gen.serialize_grouped(g))


if __name__ == '__main__':
    unittest.main()
