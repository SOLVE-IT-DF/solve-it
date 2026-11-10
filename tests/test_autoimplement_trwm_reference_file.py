import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
from autoimplement_trwm import write_reference_file


class TestWriteReferenceFile(unittest.TestCase):
    def test_bibtex_written_as_bib(self):
        with tempfile.TemporaryDirectory() as root:
            path = write_reference_file(root, "DFCite-9001", "@misc{x,\n  title = {T}\n}")
            self.assertTrue(path.endswith("DFCite-9001.bib"))

    def test_plaintext_written_as_txt(self):
        # DFCite-1163 to 1165 were plain-text citations written as .bib files
        with tempfile.TemporaryDirectory() as root:
            path = write_reference_file(root, "DFCite-9002", "Casey, E., 2020. Title. Journal 32.")
            self.assertTrue(path.endswith("DFCite-9002.txt"))
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "Casey, E., 2020. Title. Journal 32.\n")

    def test_leading_whitespace_before_bibtex(self):
        with tempfile.TemporaryDirectory() as root:
            path = write_reference_file(root, "DFCite-9003", "\n  @article{y, title = {T}}")
            self.assertTrue(path.endswith(".bib"))


if __name__ == '__main__':
    unittest.main()
