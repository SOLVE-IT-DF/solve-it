"""Every heading the Explorer's edit form emits must exist in the issue template.

The parsers look a value up by the field's *label*, not by the template's field
id, so a label that drifts from the template is not an error anywhere — the
value is simply never found and the proposed change is silently dropped. That
had already happened twice before the form was written: the Explorer prefilled
`weakness-classes` after the template renamed the field to `categories`, and it
prefilled a mitigation's linked technique without the dropdown action the
parser requires before it reads the ID.

These tests read the labels straight out of reporting_scripts/assets/editor.js,
so they fail if a label is changed on either side without the other.
"""

import os
import re
import unittest

import yaml

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')
EDITOR_JS = os.path.join(REPO_ROOT, 'reporting_scripts', 'assets', 'editor.js')
TEMPLATE_DIR = os.path.join(REPO_ROOT, '.github', 'ISSUE_TEMPLATE')

TEMPLATES = {
    'technique': '2a_update-technique-form.yml',
    'weakness': '2b_update-weakness-form.yml',
    'mitigation': '2c_update-mitigation-form.yml',
}

# Labels the body builder writes directly rather than taking from a field spec.
LITERAL_LABELS = {
    'technique': ['Any other notes'],
    'weakness': ['Any other notes'],
    'mitigation': ['Any other notes'],
}


def read_editor_source():
    with open(EDITOR_JS, encoding='utf-8') as f:
        return f.read()


def spec_blocks(source):
    """The EDIT_SPECS entry for each item type, as raw text."""
    start = source.index('const EDIT_SPECS = {')
    end = source.index('\n};', start)
    body = source[start:end]
    blocks = {}
    for item_type in TEMPLATES:
        marker = f'\n  {item_type}: {{'
        if marker not in body:
            continue
        chunk = body[body.index(marker):]
        # Up to the start of the next top-level entry, if there is one.
        nxt = re.search(r'\n  \w+: \{\n    noun:', chunk[1:])
        blocks[item_type] = chunk[:nxt.start() + 1] if nxt else chunk
    return blocks


def template_labels(filename):
    with open(os.path.join(TEMPLATE_DIR, filename), encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return {b['attributes']['label'] for b in data['body'] if b['type'] != 'markdown'}


class TestEditorLabels(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = read_editor_source()
        cls.blocks = spec_blocks(cls.source)

    def test_every_item_type_has_a_spec(self):
        self.assertEqual(set(self.blocks), set(TEMPLATES))

    def test_field_labels_exist_in_the_template(self):
        # A field whose form heading is not also an issue heading declares the
        # headings it does emit in `emits`; those are checked instead.
        for item_type, block in self.blocks.items():
            allowed = template_labels(TEMPLATES[item_type])
            for emits in re.findall(r"emits: \[([^\]]+)\]", block):
                for label in [s.strip().strip("'") for s in emits.split(',')]:
                    with self.subTest(item_type=item_type, label=label):
                        self.assertIn(label, allowed,
                                      f"'{label}' is not a field on {TEMPLATES[item_type]}")
            for label in re.findall(r"\blabel: '([^']+)'", block):
                with self.subTest(item_type=item_type, label=label):
                    if label in allowed or self._is_display_only(block, label):
                        continue
                    self.fail(f"'{label}' is not a field on {TEMPLATES[item_type]} "
                              f"and does not declare what it emits instead")

    @staticmethod
    def _is_display_only(block, label):
        """True if the field carrying this label declares its own `emits`."""
        marker = f"label: '{label}'"
        if marker not in block:
            return False
        rest = block[block.index(marker):]
        field_end = rest.index('},') if '},' in rest else len(rest)
        return 'emits:' in rest[:field_end]

    def test_id_labels_exist_in_the_template(self):
        for item_type, block in self.blocks.items():
            id_label = re.search(r"idLabel: '([^']+)'", block).group(1)
            self.assertIn(id_label, template_labels(TEMPLATES[item_type]))

    def test_literal_labels_exist_in_the_template(self):
        for item_type, labels in LITERAL_LABELS.items():
            allowed = template_labels(TEMPLATES[item_type])
            for label in labels:
                with self.subTest(item_type=item_type, label=label):
                    self.assertIn(label, allowed)

    def emitted_issue_labels(self, block):
        found = re.search(r"issueLabels: \[([^\]]+)\]", block).group(1)
        return [s.strip().strip("'") for s in found.split(',')]

    def test_content_label_matches_the_template(self):
        # autoimplement-update-item.yml and validate-revised-proposal.yml are
        # gated on this label. It has to be the same one the template declares,
        # or an Explorer submission stops dead after the preview.
        for item_type, block in self.blocks.items():
            with open(os.path.join(TEMPLATE_DIR, TEMPLATES[item_type]), encoding='utf-8') as f:
                template_declares = yaml.safe_load(f)['labels']
            expected = [l for l in template_declares if l.startswith('content: ')]
            emitted = [l for l in self.emitted_issue_labels(block) if l.startswith('content: ')]
            with self.subTest(item_type=item_type):
                self.assertEqual(emitted, expected)

    def test_explorer_label_is_emitted(self):
        # The label that says where the issue came from, read by people rather
        # than by any workflow. .github/workflows/issue-preview.yml applies the
        # same one from the body marker, for contributors whose `labels=`
        # parameter GitHub ignores.
        for item_type, block in self.blocks.items():
            with self.subTest(item_type=item_type):
                self.assertIn('explorer', self.emitted_issue_labels(block))

    def test_form_input_label_is_not_emitted(self):
        # An issue from the Explorer is a blank issue, not a form submission,
        # so the label would be untrue. It would also be inert: the only thing
        # that reads it is the `if:` on the preview jobs, which tests the
        # opened-issue event payload, and a label cannot be in that payload if
        # it is added afterwards. See the comment on the explorer-labels job.
        for item_type, block in self.blocks.items():
            with self.subTest(item_type=item_type):
                self.assertNotIn('form input', self.emitted_issue_labels(block))

    def test_dropdown_wording_matches_the_template_options(self):
        # The mitigation parser matches this dropdown by prefix, so the wording
        # the form emits has to be one of the template's own options.
        with open(os.path.join(TEMPLATE_DIR, TEMPLATES['mitigation']), encoding='utf-8') as f:
            data = yaml.safe_load(f)
        options = next(b['attributes']['options'] for b in data['body']
                       if b.get('id') == 'linked-technique-action')
        for emitted in ['Set new value (provide ID below)', 'Remove current link']:
            self.assertIn(emitted, options)
            self.assertIn(emitted, self.source)

    def test_astm_codes_match_the_knowledge_base_model(self):
        from solve_it_library.models import VALID_WEAKNESS_CLASSES
        codes = set(re.findall(r"\['(ASTM_[A-Z_]+)',", self.source))
        self.assertEqual(codes, set(VALID_WEAKNESS_CLASSES))

    def test_clear_sentinel_matches_the_parsers(self):
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, 'admin', 'issue_parsers'))
        from update_utils import CLEAR_SENTINEL
        emitted = re.search(r"const EDITOR_CLEAR = '([^']+)'", self.source).group(1)
        self.assertEqual(emitted, CLEAR_SENTINEL)


if __name__ == '__main__':
    unittest.main()
