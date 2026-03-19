"""Tests for admin/validate_kb.py phase3 weakness classes — new format."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
from validate_kb import phase3_weakness_classes, ValidationResult


class TestPhase3WeaknessClasses(unittest.TestCase):

    def _run_phase3(self, weaknesses):
        result = ValidationResult()
        phase3_weakness_classes(weaknesses, result, verbose=False)
        return result

    def test_valid_categories(self):
        weaknesses = {
            "DFW-1001": {"categories": ["ASTM_INCOMP", "ASTM_MISINT"]},
        }
        result = self._run_phase3(weaknesses)
        self.assertEqual(len(result.fails), 0)

    def test_invalid_weakness_class(self):
        weaknesses = {
            "DFW-1001": {"categories": ["INVALID_CODE"]},
        }
        result = self._run_phase3(weaknesses)
        self.assertGreater(len(result.fails), 0)

    def test_empty_categories(self):
        weaknesses = {
            "DFW-1001": {"categories": []},
        }
        result = self._run_phase3(weaknesses)
        self.assertEqual(len(result.fails), 0)

    def test_missing_categories(self):
        weaknesses = {
            "DFW-1001": {},
        }
        result = self._run_phase3(weaknesses)
        self.assertGreater(len(result.fails), 0)

    def test_duplicate_weakness_class(self):
        weaknesses = {
            "DFW-1001": {"categories": ["ASTM_INCOMP", "ASTM_INCOMP"]},
        }
        result = self._run_phase3(weaknesses)
        self.assertGreater(len(result.fails), 0)

    def test_all_valid_classes(self):
        weaknesses = {
            "DFW-1001": {"categories": [
                "ASTM_INCOMP", "ASTM_INAC_EX", "ASTM_INAC_AS",
                "ASTM_INAC_ALT", "ASTM_INAC_COR", "ASTM_MISINT",
            ]},
        }
        result = self._run_phase3(weaknesses)
        self.assertEqual(len(result.fails), 0)


if __name__ == '__main__':
    unittest.main()
