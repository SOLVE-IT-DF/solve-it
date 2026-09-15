"""The Explorer's edit form must produce issue bodies the parsers can read.

The form in reporting_scripts/assets/editor.js builds a GitHub issue body in
the shape the issue templates produce — `### <label>` headings, fenced where
the template renders a field as text. Nothing checks that at runtime, so these
tests run the real body builder (through tests/editor_body_harness.mjs) and
feed its output to the real parsers.

Skipped when Node is unavailable, since the builder is JavaScript.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_technique_issue import parse_issue_body, unknown_field_labels
import parse_update_technique_issue
import parse_update_weakness_issue
import parse_update_mitigation_issue

HERE = os.path.dirname(__file__)
HARNESS = os.path.join(HERE, 'editor_body_harness.mjs')

# These mirror the fixtures in the harness. Kept side by side on purpose: if
# one drifts from the other the assertions below stop meaning anything, and a
# reader can see both without switching language.
TECHNIQUE = {
    "id": "DFT-1043",
    "name": "Read bitstream",
    "description": "Original description.",
    "details": "Original details.",
    "synonyms": ["imaging", "acquisition"],
    "examples": ["dd"],
    "subtechniques": ["DFT-1044"],
    "weaknesses": ["DFW-1001", "DFW-1002"],
    "CASE_input_classes": ["https://ontology.unifiedcyberontology.org/uco/observable/Device"],
    "CASE_output_classes": ["https://ontology.unifiedcyberontology.org/uco/observable/File"],
    "references": [{"DFCite_id": "DFCite-1001", "relevance_summary_280": "Original relevance."}],
}

WEAKNESS = {
    "id": "DFW-1001",
    "name": "Original weakness name",
    "description": "",
    "categories": ["ASTM_INCOMP"],
    "mitigations": ["DFM-1001"],
    "references": [],
}

MITIGATION = {
    "id": "DFM-1001",
    "name": "Original mitigation name",
    "description": "",
    "technique": "DFT-1050",
    "references": [],
}


def run_harness():
    node = shutil.which('node')
    if not node:
        raise unittest.SkipTest("node is not installed")
    result = subprocess.run([node, HARNESS], capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"harness failed:\n{result.stderr}")
    return json.loads(result.stdout)


class EditorBodyTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data = run_harness()
        cls.cases = cls.data['cases']
        cls.labels = cls.data['labels']
        # The harness echoes its fixtures; if either copy drifts, every
        # assertion below would be comparing against the wrong original.
        for name, ours in (('TECHNIQUE', TECHNIQUE), ('WEAKNESS', WEAKNESS), ('MITIGATION', MITIGATION)):
            if cls.data['fixtures'][name] != ours:
                raise AssertionError(f"{name} fixture differs between editor_body_harness.mjs and this file")

    def fields(self, name):
        return parse_issue_body(self.cases[name]['body'])

    def apply_technique(self, name, current=None):
        updated, _, _, _ = parse_update_technique_issue.apply_updates(
            copy.deepcopy(current or TECHNIQUE), self.fields(name))
        return updated


class TestMarker(EditorBodyTestCase):
    """The body starts with a marker that issue-preview.yml turns into labels,
    because GitHub ignores the `labels=` query parameter for contributors who
    could not add those labels by hand."""

    def test_body_starts_with_the_marker_for_its_item_type(self):
        id_headings = {'### Technique ID': 'technique', '### Weakness ID': 'weakness', '### Mitigation ID': 'mitigation'}
        for name, case in self.cases.items():
            kind = next(k for heading, k in id_headings.items() if heading in case['body'])
            self.assertTrue(case['body'].startswith(f'<!-- solveit-explorer: update-{kind} -->\n'),
                            f"{name} body does not start with its marker")

    def test_marker_matches_what_the_workflow_greps_for(self):
        workflow = open(os.path.join(HERE, '..', '.github', 'workflows', 'issue-preview.yml')).read()
        self.assertIn("<!-- solveit-explorer: update-(technique|weakness|mitigation) -->", workflow)

    def test_marker_is_invisible_to_the_parser(self):
        fields = self.fields('technique_untouched')
        self.assertEqual(list(fields), ['Technique ID'])


class TestValidation(EditorBodyTestCase):
    """editorProblems() is what stops a broken submission leaving the form."""

    def problems(self, name):
        return self.cases[name]['problems']

    def test_a_fence_in_a_value_is_refused(self):
        self.assertTrue(any('```' in p for p in self.problems('problem_fence_in_value')))

    def test_an_overlong_relevance_summary_is_refused(self):
        self.assertTrue(any('280' in p for p in self.problems('problem_relevance_too_long')))

    def test_an_unknown_id_is_refused(self):
        self.assertTrue(any('DFW-9999' in p for p in self.problems('problem_unknown_weakness')))

    def test_an_empty_name_is_refused(self):
        self.assertTrue(any('name' in p.lower() for p in self.problems('problem_empty_name')))

    def test_linking_without_choosing_a_technique_is_refused(self):
        self.assertEqual(len(self.problems('problem_link_without_id')), 1)

    def test_an_overlong_url_is_refused(self):
        self.assertTrue(any('too long' in p for p in self.problems('problem_url_too_long')))

    def test_a_clean_change_has_no_problems(self):
        self.assertEqual(self.problems('clean_change_has_no_problems'), [])


class TestTechniqueRoundTrip(EditorBodyTestCase):

    def test_id_is_always_sent(self):
        self.assertEqual(self.fields('technique_untouched').get('Technique ID'), 'DFT-1043')

    def test_untouched_item_sends_nothing_but_the_id(self):
        self.assertEqual(list(self.fields('technique_untouched')), ['Technique ID'])

    def test_untouched_item_applies_as_no_change(self):
        self.assertEqual(self.apply_technique('technique_untouched'), TECHNIQUE)

    def test_scalar_changes_apply(self):
        updated = self.apply_technique('technique_scalars')
        self.assertEqual(updated['name'], 'Read bitstream from a device')
        self.assertEqual(updated['description'], 'A revised description with a [DFCite-1001] citation.')

    def test_unchanged_fields_are_left_alone(self):
        # The whole point of sending only what changed: everything else must
        # come through untouched rather than being rewritten to a stale value.
        updated = self.apply_technique('technique_scalars')
        self.assertEqual(updated['details'], TECHNIQUE['details'])
        self.assertEqual(updated['synonyms'], TECHNIQUE['synonyms'])
        self.assertEqual(updated['weaknesses'], TECHNIQUE['weaknesses'])
        self.assertEqual(updated['references'], TECHNIQUE['references'])

    def test_emptied_list_is_sent_as_the_clear_sentinel(self):
        self.assertEqual(self.fields('technique_clear_synonyms').get('Synonyms'), '_none_')

    def test_emptied_list_applies_as_an_empty_list(self):
        self.assertEqual(self.apply_technique('technique_clear_synonyms')['synonyms'], [])

    def test_list_replacement_applies(self):
        updated = self.apply_technique('technique_lists')
        self.assertEqual(updated['weaknesses'], ['DFW-1001', 'DFW-9999'])
        self.assertEqual(updated['CASE_output_classes'], [
            'https://ontology.unifiedcyberontology.org/uco/observable/File',
            'https://ontology.unifiedcyberontology.org/uco/observable/RasterPicture',
        ])

    def test_unchanged_list_is_not_sent(self):
        self.assertNotIn('Ontology input classes', self.fields('technique_lists'))

    def test_references_carry_their_relevance_summaries(self):
        raw = self.fields('technique_references')['References']
        self.assertIn('DFCite-1001 | A revised relevance summary.', raw)
        self.assertIn('DFCite-1002 | Newly added.', raw)

    def test_emptied_references_apply_as_an_empty_list(self):
        self.assertEqual(self.apply_technique('technique_clear_references')['references'], [])

    def test_emptied_details_are_sent_as_the_sentinel_and_apply_as_empty(self):
        # A blank value would mean "leave alone" at the parser, so the form
        # cannot send '' for a cleared field; it sends `_none_` instead.
        self.assertEqual(self.fields('technique_clear_details')['New details'], '_none_')
        self.assertEqual(self.apply_technique('technique_clear_details')['details'], '')

    def test_additional_and_notes_fields_are_sent(self):
        fields = self.fields('technique_notes_and_new_weaknesses')
        self.assertEqual(fields['Propose new weaknesses'], 'Imaging may miss data in hidden areas')
        self.assertIn('firmware regions', fields['Any other notes'])

    def test_a_heading_inside_a_value_is_not_read_as_a_field(self):
        # A contributor can legitimately type '### Weakness IDs' into the
        # details. Fencing keeps it inside that value instead of starting a new
        # field and silently rewriting the weakness list.
        fields = self.fields('technique_heading_in_value')
        self.assertIn('### Weakness IDs', fields['New details'])
        self.assertNotIn('Weakness IDs', fields)
        self.assertEqual(self.apply_technique('technique_heading_in_value')['weaknesses'],
                         TECHNIQUE['weaknesses'])

    def test_no_unrecognised_headings_are_emitted(self):
        known = set(self.labels['technique']['fields'])
        known.update({self.labels['technique']['idLabel'], 'Any other notes'})
        for name, case in self.cases.items():
            if not name.startswith('technique'):
                continue
            unknown = unknown_field_labels(parse_issue_body(case['body']), known)
            self.assertEqual(unknown, [], f"{name} emitted unknown headings: {unknown}")


class TestWeaknessRoundTrip(EditorBodyTestCase):

    def apply(self, name):
        updated, _, _, errors = parse_update_weakness_issue.apply_updates(
            copy.deepcopy(WEAKNESS), self.fields(name))
        self.assertEqual(errors, [], "the form emitted categories the parser rejects")
        return updated

    def test_categories_apply(self):
        self.assertEqual(self.apply('weakness_categories')['categories'],
                         ['ASTM_INCOMP', 'ASTM_MISINT'])

    def test_emptied_mitigations_apply_as_an_empty_list(self):
        self.assertEqual(self.apply('weakness_clear_mitigations')['mitigations'], [])

    def test_emptied_description_applies_as_empty(self):
        updated, _, _, _ = parse_update_weakness_issue.apply_updates(
            dict(WEAKNESS, description='Some description'), self.fields('weakness_clear_description'))
        self.assertEqual(updated['description'], '')

    def test_categories_are_not_fenced(self):
        # The weakness form does not render Categories as text, so the body
        # should not fence it either.
        self.assertNotIn('```', self.cases['weakness_categories']['body'].split('### Categories')[1])


class TestMitigationRoundTrip(EditorBodyTestCase):

    def apply(self, name):
        updated, _, _, _ = parse_update_mitigation_issue.apply_updates(
            copy.deepcopy(MITIGATION), self.fields(name))
        return updated

    def test_setting_a_link_uses_the_dropdown_wording_the_parser_matches(self):
        fields = self.fields('mitigation_set_link')
        self.assertTrue(fields['Linked technique action'].startswith('Set new value'))
        self.assertEqual(self.apply('mitigation_set_link')['technique'], 'DFT-1099')

    def test_removing_a_link_removes_the_key(self):
        self.assertNotIn('technique', self.apply('mitigation_remove_link'))

    def test_leaving_the_link_alone_sends_no_action(self):
        fields = self.fields('mitigation_keep_link')
        self.assertNotIn('Linked technique action', fields)
        self.assertEqual(self.apply('mitigation_keep_link')['technique'], 'DFT-1050')


class TestIssueUrl(EditorBodyTestCase):

    def test_url_targets_a_blank_issue_not_a_template(self):
        # A template URL is what GitHub now locks the prefilled fields of. The
        # whole approach depends on not using one.
        for name, case in self.cases.items():
            self.assertNotIn('template=', case['url'], f"{name} still targets an issue template")

    def test_url_carries_the_labels_the_actions_key_off(self):
        # Only for a contributor GitHub lets label an issue; for everyone else
        # the parameter is ignored and issue-preview.yml applies the same set
        # from the body marker.
        url = self.cases['technique_scalars']['url']
        self.assertIn('content%3A+update+technique', url)
        self.assertIn('explorer', url)

    def test_url_does_not_claim_the_issue_came_from_a_form(self):
        # A blank issue is not a form submission. See the comment above
        # EDIT_SPECS in editor.js for why the label is both untrue and inert.
        for name, case in self.cases.items():
            with self.subTest(case=name):
                self.assertNotIn('form+input', case['url'])

    def test_urls_stay_well_under_the_length_limit(self):
        # The `problem_` cases include one that is over the limit on purpose.
        for name, case in self.cases.items():
            if name.startswith('problem_'):
                continue
            self.assertLess(len(case['url']), 8000, f"{name} produced a {len(case['url'])} character URL")


if __name__ == '__main__':
    unittest.main()
