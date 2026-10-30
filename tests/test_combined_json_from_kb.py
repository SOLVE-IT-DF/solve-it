import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library import KnowledgeBase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
import generate_combined_json_from_kb


class TestCombinedJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase('.', 'solve-it.json')
        cls.combined = generate_combined_json_from_kb.build_combined_json(cls.kb)

    def test_existing_sections_present(self):
        for key in ("techniques", "weaknesses", "mitigations", "objectives"):
            self.assertIn(key, self.combined)
        self.assertIn("DFT-1001", self.combined["techniques"])

    def test_every_citation_exported(self):
        citations = self.combined["citations"]
        self.assertEqual(set(citations), set(self.kb.citations))
        for cite_id, citation in citations.items():
            self.assertEqual(set(citation), {"bibtex", "plaintext", "display_text"})
            self.assertTrue(citation["display_text"], cite_id)

    def test_bibtex_only_citation_gets_display_text(self):
        bib_only = [c for c in self.combined["citations"].values()
                    if c["bibtex"] and not c["plaintext"]]
        self.assertTrue(bib_only)
        for citation in bib_only:
            self.assertNotIn("@", citation["display_text"][:1])


if __name__ == '__main__':
    unittest.main()
