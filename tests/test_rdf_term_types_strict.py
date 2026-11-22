"""
The scheduled ontology build must not publish a knowledge base whose
input/output terms have lost their type declarations.

The generator downloads CASE/UCO, SOLVE-IT and projectvic ontology modules to
work out whether each term is a class or a property. A failed download used to
log a warning and carry on, so a partial download produced output without those
declarations and the build still reported success. With require_term_types the
same situation raises instead.
"""

import os
import sys
import unittest
from unittest import mock

from rdflib import OWL, URIRef

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
from solve_it_library import KnowledgeBase  # noqa: E402
import generate_rdf_from_kb as gen  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')
EXPERT_REPORT = 'https://cacontology.projectvic.org/case-management#ExpertReport'


class _FakeLookup:
    """Types every term as a class except those listed as unresolvable."""

    def __init__(self, unresolvable=()):
        self.unresolvable = set(unresolvable)

    def term_type(self, uri):
        return None if str(uri) in self.unresolvable else OWL.Class


class TestRequireTermTypes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase(ROOT, 'solve-it.json')

    def _build(self, lookup, **kwargs):
        with mock.patch.object(gen, 'load_term_type_lookup', return_value=lookup):
            return gen.create_rdf_graph(self.kb, **kwargs)

    def test_missing_lookup_is_fatal_when_required(self):
        with self.assertRaises(gen.TermTypesUnresolvedError):
            self._build(None, require_term_types=True)

    def test_one_unresolved_term_is_fatal_when_required(self):
        with self.assertRaises(gen.TermTypesUnresolvedError) as ctx:
            self._build(_FakeLookup([EXPERT_REPORT]), require_term_types=True)
        self.assertIn(EXPERT_REPORT, str(ctx.exception))

    def test_default_still_tolerates_an_incomplete_lookup(self):
        g = self._build(_FakeLookup([EXPERT_REPORT]))
        self.assertNotIn((URIRef(EXPERT_REPORT), gen.RDF.type, OWL.Class), g)

    def test_fully_resolved_lookup_passes_when_required(self):
        g = self._build(_FakeLookup(), require_term_types=True)
        self.assertIn((URIRef(EXPERT_REPORT), gen.RDF.type, OWL.Class), g)


if __name__ == '__main__':
    unittest.main()
