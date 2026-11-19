"""Mitigations are output following the metaclass pattern, as techniques are.

Each mitigation must be an instance of solveit-core:Mitigation AND an owl:Class
in its own right, rdfs:subClassOf solveit-core:SolveitMitigation. UCO 1.5.0
requires every instance of uco-action:Technique (which solveit-core:Mitigation
specialises) to be an owl:Class descending from uco-action:Action, so a
mitigation output as a plain individual fails CASE validation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))

from rdflib import OWL, RDF, RDFS  # noqa: E402

from solve_it_library import KnowledgeBase  # noqa: E402
import generate_rdf_from_kb as gen  # noqa: E402


class TestMitigationMetaclass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase('.', 'solve-it.json')
        cls.g = gen.create_rdf_graph(cls.kb)
        cls.mitigations = set(cls.g.subjects(RDF.type, gen.SOLVEIT_CORE.Mitigation))

    def test_every_kb_mitigation_is_output(self):
        self.assertEqual(len(self.mitigations), len(self.kb.list_mitigations()))

    def test_each_mitigation_is_a_class(self):
        missing = [m for m in self.mitigations if (m, RDF.type, OWL.Class) not in self.g]
        self.assertEqual(missing, [])

    def test_each_mitigation_subclasses_solveit_mitigation(self):
        missing = [m for m in self.mitigations
                   if (m, RDFS.subClassOf, gen.SOLVEIT_CORE.SolveitMitigation) not in self.g]
        self.assertEqual(missing, [])

    def test_mitigation_iris_are_unchanged(self):
        for mit_id in self.kb.list_mitigations():
            self.assertIn(gen.SOLVEIT_DATA[f"mitigation{mit_id}"], self.mitigations)


if __name__ == '__main__':
    unittest.main()
