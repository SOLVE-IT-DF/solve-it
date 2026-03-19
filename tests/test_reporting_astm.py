"""Tests for weakness classes in reporting outputs — new format."""

import unittest
import sys
import os
import io
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))

from solve_it_library import KnowledgeBase
from generate_html_from_kb import weakness_cats, WEAKNESS_CATS, CAT_LABELS
import generate_tsv_from_kb


class TestHtmlWeaknessCats(unittest.TestCase):

    def test_html_weakness_cats_with_classes(self):
        w = {"categories": ["ASTM_INCOMP", "ASTM_MISINT"]}
        cats = weakness_cats(w)
        self.assertEqual(cats, ["ASTM_INCOMP", "ASTM_MISINT"])

    def test_html_weakness_cats_empty(self):
        w = {"categories": []}
        cats = weakness_cats(w)
        self.assertEqual(cats, [])

    def test_html_weakness_cats_missing_key(self):
        w = {}
        cats = weakness_cats(w)
        self.assertEqual(cats, [])

    def test_html_weakness_cats_all(self):
        w = {"categories": list(WEAKNESS_CATS)}
        cats = weakness_cats(w)
        self.assertEqual(cats, WEAKNESS_CATS)

    def test_cat_labels_use_astm_prefix(self):
        for key in CAT_LABELS:
            self.assertTrue(key.startswith("ASTM_"))


class TestTsvAstmColumns(unittest.TestCase):

    def test_tsv_astm_columns(self):
        kb = KnowledgeBase('.', 'solve-it.json')
        captured = io.StringIO()
        with redirect_stdout(captured):
            generate_tsv_from_kb.print_weaknesses(kb, True)
        output = captured.getvalue()
        # Header should contain ASTM codes
        self.assertIn("INCOMP", output)
        self.assertIn("INAC-EX", output)
        # DFW-1001 has ASTM_INCOMP → should show X
        self.assertIn("DFW-1001", output)


class TestMdWeaknessCategories(unittest.TestCase):

    def test_md_weakness_display(self):
        from generate_md_from_kb import get_weakness_categories
        w = {"categories": ["ASTM_INCOMP", "ASTM_MISINT"]}
        result = get_weakness_categories(w)
        self.assertIn("INCOMP", result)
        self.assertIn("MISINT", result)

    def test_md_weakness_empty(self):
        from generate_md_from_kb import get_weakness_categories
        w = {"categories": []}
        result = get_weakness_categories(w)
        self.assertEqual(result, "")


class TestRdfWeakness(unittest.TestCase):

    def test_rdf_weakness_has_class_triples(self):
        """Verify RDF generator uses hasWeaknessClass property."""
        from generate_rdf_from_kb import create_rdf_graph
        kb = KnowledgeBase('.', 'solve-it.json')
        g = create_rdf_graph(kb)
        rdf_output = g.serialize(format='turtle')
        self.assertIn("hasWeaknessClass", rdf_output)
        # Should NOT contain old boolean properties
        self.assertNotIn("mayResultInINCOMP", rdf_output)


class TestExcelAstmColumns(unittest.TestCase):

    def test_excel_module_imports(self):
        """Verify generate_excel module loads correctly."""
        import generate_excel_from_kb
        self.assertTrue(hasattr(generate_excel_from_kb, 'format_headings_in_workbook'))


if __name__ == '__main__':
    unittest.main()
