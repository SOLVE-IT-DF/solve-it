"""Tests for form generators — new format (textarea for weakness classes)."""

import unittest
import sys
import os
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')
WEAKNESS_FORM = os.path.join(REPO_ROOT, '.github', 'ISSUE_TEMPLATE', '1b_propose-new-weakness-form.yml')
UPDATE_WEAKNESS_FORM = os.path.join(REPO_ROOT, '.github', 'ISSUE_TEMPLATE', '2b_update-weakness-form.yml')


class TestFormGenerators(unittest.TestCase):

    def test_weakness_form_has_class_codes(self):
        with open(WEAKNESS_FORM) as f:
            content = f.read()
        for code in ["ASTM_INCOMP", "ASTM_INAC_EX", "ASTM_INAC_AS",
                      "ASTM_INAC_ALT", "ASTM_INAC_COR", "ASTM_MISINT"]:
            self.assertIn(code, content)

    def test_weakness_form_uses_textarea(self):
        with open(WEAKNESS_FORM) as f:
            data = yaml.safe_load(f)
        # Find the weakness classes field
        classes_field = None
        for field in data['body']:
            if field.get('id') == 'categories':
                classes_field = field
                break
        self.assertIsNotNone(classes_field)
        self.assertEqual(classes_field['type'], 'textarea')

    def test_update_weakness_form_has_class_codes(self):
        with open(UPDATE_WEAKNESS_FORM) as f:
            content = f.read()
        for code in ["ASTM_INCOMP", "ASTM_INAC_EX", "ASTM_INAC_AS",
                      "ASTM_INAC_ALT", "ASTM_INAC_COR", "ASTM_MISINT"]:
            self.assertIn(code, content)

    def test_form_yaml_is_valid(self):
        for form_path in [WEAKNESS_FORM, UPDATE_WEAKNESS_FORM]:
            with open(form_path) as f:
                data = yaml.safe_load(f)
            self.assertIn('name', data)
            self.assertIn('body', data)
            self.assertIsInstance(data['body'], list)


if __name__ == '__main__':
    unittest.main()
