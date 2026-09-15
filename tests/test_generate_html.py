"""
Regression tests for the SOLVE-IT HTML explorer generator.

Covers:
- Deep linking with both old (T/W/M) and new (DFT-/DFW-/DFM-) ID prefixes
- Contributor credit extraction across file renames
"""

import unittest
import re
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
from generate_html_from_kb import extract_git_credits, _build_rename_map

REPO_ROOT = Path(os.path.dirname(__file__)).parent


class TestDeepLinks(unittest.TestCase):
    """Verify that the generated HTML handles both old and new-style deep links."""

    @classmethod
    def setUpClass(cls):
        html_path = REPO_ROOT / "solveit-viewer.html"
        if not html_path.exists():
            raise unittest.SkipTest("solveit-viewer.html not found — run generate_html_from_kb.py first")
        cls.html = html_path.read_text()

    def test_new_prefix_deep_links(self):
        """New-style DFT-/DFW-/DFM- hash links should be handled."""
        self.assertIn("startsWith('DFT-')", self.html)
        self.assertIn("startsWith('DFW-')", self.html)
        self.assertIn("startsWith('DFM-')", self.html)

    def test_old_prefix_redirect(self):
        """Old-style T/W/M hash links should be redirected to new prefixes."""
        # The JS should detect old prefixes and rewrite the hash
        self.assertRegex(self.html, r"/\^\[TWM\]\\d/")
        # Should map old prefixes to new ones
        self.assertIn("T:'DFT-'", self.html)
        self.assertIn("W:'DFW-'", self.html)
        self.assertIn("M:'DFM-'", self.html)

    def test_old_prefix_uses_replace(self):
        """Old-prefix redirect should use location.replace to avoid polluting history."""
        self.assertIn("location.replace('#' + id)", self.html)


class TestGitCredits(unittest.TestCase):
    """Verify contributor extraction follows file renames and doesn't regress."""

    @classmethod
    def setUpClass(cls):
        cls.credits = extract_git_credits(REPO_ROOT)
        cls.all_contributors = set()
        for v in cls.credits.values():
            cls.all_contributors.update(v["contributors"])

    def test_rename_map_populated(self):
        """The rename map should detect the T->DFT, W->DFW, M->DFM renames."""
        rename_map = _build_rename_map(REPO_ROOT)
        self.assertGreater(len(rename_map), 0)
        # Spot-check a known rename
        self.assertEqual(rename_map.get("T1134"), "DFT-1134")

    def test_known_contributor_credited_across_rename(self):
        """Céline Vanini authored T1134 (now DFT-1134) and must appear as contributor."""
        item = self.credits.get("DFT-1134", {})
        self.assertIn("Céline Vanini", item.get("contributors", []))

    def test_unique_contributor_count_does_not_regress(self):
        """Total unique contributors should not decrease (currently 7)."""
        self.assertGreaterEqual(len(self.all_contributors), 7,
            f"Unique contributor count dropped to {len(self.all_contributors)}: "
            f"{sorted(self.all_contributors)}")

    def test_total_contributor_entries_do_not_regress(self):
        """Total contributor entries across all items should not decrease (currently 961)."""
        total = sum(len(v["contributors"]) for v in self.credits.values())
        self.assertGreaterEqual(total, 961,
            f"Total contributor entries dropped to {total} — "
            f"rename following may be broken")


class TestHiddenFieldsCoverage(unittest.TestCase):
    """Every hideable field in all_fields must have a HIDDEN_FIELDS.has() check in the JS."""

    @classmethod
    def setUpClass(cls):
        src_path = REPO_ROOT / "reporting_scripts" / "generate_html_from_kb.py"
        cls.source = src_path.read_text()

    def test_all_fields_includes_credits_fields(self):
        """Regression: properties, contributors, reviewers must be in all_fields."""
        # Extract the all_fields list from the source
        match = re.search(r"all_fields\s*=\s*\[([^\]]+)\]", self.source, re.DOTALL)
        self.assertIsNotNone(match, "Could not find all_fields list in source")
        fields = re.findall(r"'(\w+)'", match.group(1))
        for field in ('properties', 'contributors', 'reviewers'):
            self.assertIn(field, fields,
                f"'{field}' missing from all_fields — it won't be hideable via config")

    def test_hideable_fields_have_js_checks(self):
        """Every field in all_fields (except id/name) must have a HIDDEN_FIELDS.has() guard."""
        match = re.search(r"all_fields\s*=\s*\[([^\]]+)\]", self.source, re.DOTALL)
        self.assertIsNotNone(match)
        fields = re.findall(r"'(\w+)'", match.group(1))
        # id and name are always shown
        for field in fields:
            if field in ('id', 'name'):
                continue
            self.assertIn(
                f"HIDDEN_FIELDS.has('{field}')",
                self.source,
                f"No HIDDEN_FIELDS.has('{field}') check found in JS — "
                f"this field won't be hidden even when configured as hidden")



class TestEditorAssets(unittest.TestCase):
    """The edit form's CSS and JavaScript live in reporting_scripts/assets/ and
    are inlined at build time, so the generated page stays a single file that
    GitHub Pages can serve on its own. These check they actually arrive.

    The page is generated here rather than read from solveit-viewer.html, so
    the tests run in this repository's own CI, where nothing builds that file
    first. Skipping the git-credit pass keeps the build well under a second."""

    @classmethod
    def setUpClass(cls):
        from generate_html_from_kb import load_from_local, build_indices, generate_html
        db = load_from_local(str(REPO_ROOT))
        cls.html = generate_html(db, build_indices(db))

    def test_editor_javascript_is_inlined(self):
        self.assertIn("function openEditor(", self.html)
        self.assertIn("const EDIT_SPECS = {", self.html)

    def test_editor_css_is_inlined(self):
        self.assertIn(".editor-overlay", self.html)
        self.assertIn(".editor-chip", self.html)

    def test_page_has_no_external_asset_requests(self):
        # Inlining is the point: a stylesheet or script fetched at runtime would
        # break the single-file page and the offline copies people keep.
        self.assertNotIn('<script src=', self.html)
        for link in re.findall(r'<link[^>]*rel="stylesheet"[^>]*>', self.html):
            self.assertIn('fonts.googleapis.com', link,
                          "only the web font stylesheet may be external")

    def test_ontology_terms_are_baked_in(self):
        self.assertIn("const ONTOLOGY_TERMS = [", self.html)
        self.assertIn("unifiedcyberontology.org", self.html)

    def test_edit_button_opens_the_form_rather_than_a_prefilled_template(self):
        self.assertIn("openEditor(", self.html)
        self.assertNotIn("2a_update-technique-form.yml", self.html)
        self.assertNotIn("2b_update-weakness-form.yml", self.html)
        self.assertNotIn("2c_update-mitigation-form.yml", self.html)

    def test_assets_cannot_terminate_the_tags_they_are_inlined_into(self):
        # A literal '</script>' or '</style>' anywhere in an asset would close
        # the block early and break the page, and it would still look correct
        # in the source file. Cheap to check, silent and total if missed.
        for name in ('editor.js', 'editor.css'):
            text = (REPO_ROOT / 'reporting_scripts' / 'assets' / name).read_text()
            self.assertNotIn('</script', text.lower(), f'{name} would close the script block')
            self.assertNotIn('</style', text.lower(), f'{name} would close the style block')

    def test_propose_new_forms_still_use_their_templates(self):
        # Only the *update* path moved into the page; proposing a new item is
        # unchanged and still opens the issue form directly.
        self.assertIn("1a_propose-new-technique-form.yml", self.html)
        self.assertIn("1d_propose-new-reference-form.yml", self.html)


if __name__ == '__main__':
    unittest.main()
