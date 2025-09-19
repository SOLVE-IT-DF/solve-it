import unittest
from contextlib import redirect_stdout
import io
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library import KnowledgeBase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
import generate_tsv_from_kb

class MyTestCase(unittest.TestCase):
    def test_print_objective_runs_without_error(self):
        kb = KnowledgeBase('.', 'solve-it.json')
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_objectives(kb, False)
        self.assertIn("Objective", captured_output.getvalue())

    def test_print_technique_runs_without_error(self):
        kb = KnowledgeBase('.', 'solve-it.json')
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_techniques(kb, False)
        self.assertIn("T1001", captured_output.getvalue())

        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_techniques(kb, True)
        self.assertIn("Description", captured_output.getvalue())

        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_techniques(kb, True)
        self.assertIn("Synonyms", captured_output.getvalue())

    def test_print_weakness_runs_without_error(self):
        kb = KnowledgeBase('.', 'solve-it.json')
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_weaknesses(kb, False)
        self.assertIn("W1001", captured_output.getvalue())

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_weaknesses(kb, True)
        self.assertIn("INAC", captured_output.getvalue())

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_weaknesses(kb, True)
        test_str = 'W1001\tExcluding a device that contains relevant information\tx\t\t\t\t\t\n'
        self.assertIn(test_str, captured_output.getvalue())

    def test_print_mitigations_runs_without_error(self):
        kb = KnowledgeBase('.', 'solve-it.json')
        captured_output = io.StringIO()

        with redirect_stdout(captured_output):
            generate_tsv_from_kb.print_mitigations(kb, False)
        self.assertIn("M1001", captured_output.getvalue())




if __name__ == '__main__':
    unittest.main()
