"""Tests for admin/issue_parsers/parse_trwm_submission.py."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin', 'issue_parsers'))
from parse_trwm_submission import (
    normalize_to_kb_schema, resolve_bare_references, validate_submission,
    TECHNIQUE_FIELDS, WEAKNESS_FIELDS, MITIGATION_FIELDS,
)


class TestNormalizeReferences(unittest.TestCase):
    """normalize_to_kb_schema acts as a safety net — post-resolver all refs
    should already be dicts, but any stray bare strings are stripped."""

    def test_bare_strings_filtered_out(self):
        item = {"id": "DFT-9999", "name": "Test", "references": ["timeline"]}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [])

    def test_dict_references_preserved(self):
        ref = {"DFCite_id": "DFCite-1001", "relevance_summary_280": "Relevant"}
        item = {"id": "DFT-9999", "name": "Test", "references": [ref]}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [ref])

    def test_mixed_list_keeps_only_dicts(self):
        ref = {"DFCite_id": "DFCite-1001", "relevance_summary_280": "Relevant"}
        item = {"id": "DFT-9999", "name": "Test", "references": ["bad", ref, 42]}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [ref])

    def test_empty_references_unchanged(self):
        item = {"id": "DFT-9999", "name": "Test", "references": []}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [])

    def test_missing_references_defaults_to_empty(self):
        item = {"id": "DFT-9999", "name": "Test"}
        result = normalize_to_kb_schema(item, TECHNIQUE_FIELDS)
        self.assertEqual(result["references"], [])


class TestValidateSubmissionReferences(unittest.TestCase):
    """After resolve_bare_references runs, validate_submission should no
    longer emit a non-dict-refs warning — all refs are dicts by then."""

    def test_no_warning_for_valid_references(self):
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {
                    "id": "DFT-temp-0001",
                    "name": "Test",
                    "description": "desc",
                    "weaknesses": [],
                    "references": [{"DFCite_id": "DFCite-1001"}],
                }
            },
            "weaknesses": {},
            "mitigations": {},
        }
        new_items = {
            "techniques": [trwm_data["techniques"]["DFT-temp-0001"]],
            "weaknesses": [],
            "mitigations": [],
        }
        notes = validate_submission(trwm_data, new_items)
        warning_msgs = [msg for level, msg in notes if level == "warning"]
        self.assertFalse(
            any("non-dict" in msg for msg in warning_msgs),
            f"Unexpected non-dict warning: {warning_msgs}"
        )


class TestResolveBareReferences(unittest.TestCase):
    """Bare BibTeX/plaintext refs should be strict-matched or turned into
    DFCite-____-N placeholders — never silently dropped."""

    def _make_project_root(self, corpus_entries):
        """Create a temp project root with the given {cite_id: file_content} entries."""
        root = tempfile.mkdtemp(prefix="trwm-resolver-test-")
        refs_dir = os.path.join(root, "data", "references")
        os.makedirs(refs_dir)
        for cite_id, (ext, content) in corpus_entries.items():
            with open(os.path.join(refs_dir, f"{cite_id}.{ext}"), "w",
                      encoding="utf-8") as f:
                f.write(content)
        return root

    def test_unmatched_bare_string_gets_placeholder(self):
        root = self._make_project_root({})
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {
                    "id": "DFT-temp-0001",
                    "references": [
                        "@article{foo2026, title={A totally new paper}, author={Foo, Bar}, year={2026}}"
                    ],
                }
            },
            "weaknesses": {},
            "mitigations": {},
        }
        placeholders = resolve_bare_references(trwm_data, root)
        refs = trwm_data["techniques"]["DFT-temp-0001"]["references"]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["DFCite_id"], "DFCite-____-1")
        self.assertIn("DFCite-____-1", placeholders)
        self.assertTrue(placeholders["DFCite-____-1"]["text"].startswith("@article"))

    def test_bibtex_matching_existing_bib_gets_real_id(self):
        # Corpus entry with a known title/year/author
        bib = (
            "@article{known, title={A digital forensic view of Windows 10 notifications}, "
            "author={Domingues, P and Andrade, L}, year={2022}, journal={Forensic Sciences}}"
        )
        root = self._make_project_root({"DFCite-9001": ("bib", bib)})
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {
                    "id": "DFT-temp-0001",
                    "references": [
                        "@article{user_submitted, "
                        "title={A digital forensic view of Windows 10 notifications}, "
                        "author={Domingues, Patricio and Andrade, Luis}, year={2022}}"
                    ],
                }
            },
            "weaknesses": {},
            "mitigations": {},
        }
        placeholders = resolve_bare_references(trwm_data, root)
        refs = trwm_data["techniques"]["DFT-temp-0001"]["references"]
        self.assertEqual(refs[0]["DFCite_id"], "DFCite-9001")
        self.assertEqual(placeholders, {})

    def test_identical_bare_strings_dedupe_to_one_placeholder(self):
        root = self._make_project_root({})
        bib = "@article{foo, title={Same paper everywhere}, year={2024}, author={Foo, B}}"
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {"id": "DFT-temp-0001", "references": [bib]},
            },
            "weaknesses": {
                "DFW-temp-0001": {"id": "DFW-temp-0001", "references": [bib]},
            },
            "mitigations": {
                "DFM-temp-0001": {"id": "DFM-temp-0001", "references": [bib]},
            },
        }
        placeholders = resolve_bare_references(trwm_data, root)
        self.assertEqual(len(placeholders), 1)
        placeholder = next(iter(placeholders.keys()))
        self.assertEqual(
            trwm_data["techniques"]["DFT-temp-0001"]["references"][0]["DFCite_id"],
            placeholder,
        )
        self.assertEqual(
            trwm_data["weaknesses"]["DFW-temp-0001"]["references"][0]["DFCite_id"],
            placeholder,
        )
        self.assertEqual(
            trwm_data["mitigations"]["DFM-temp-0001"]["references"][0]["DFCite_id"],
            placeholder,
        )

    def test_dict_references_pass_through_unchanged(self):
        root = self._make_project_root({})
        ref = {"DFCite_id": "DFCite-1001", "relevance_summary_280": "note"}
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {"id": "DFT-temp-0001", "references": [ref]},
            },
            "weaknesses": {},
            "mitigations": {},
        }
        placeholders = resolve_bare_references(trwm_data, root)
        self.assertEqual(
            trwm_data["techniques"]["DFT-temp-0001"]["references"], [ref],
        )
        self.assertEqual(placeholders, {})

    def test_url_overlap_matches_existing(self):
        # URL-based strict match should fire via match_reference (not signature)
        root = self._make_project_root({
            "DFCite-7777": ("txt", "Smith 2020, A paper. Available at: https://example.com/paper.pdf"),
        })
        trwm_data = {
            "techniques": {
                "DFT-temp-0001": {
                    "id": "DFT-temp-0001",
                    "references": ["Jones, J. 2020, A different title. https://example.com/paper.pdf"],
                }
            },
            "weaknesses": {},
            "mitigations": {},
        }
        placeholders = resolve_bare_references(trwm_data, root)
        refs = trwm_data["techniques"]["DFT-temp-0001"]["references"]
        self.assertEqual(refs[0]["DFCite_id"], "DFCite-7777")
        self.assertEqual(placeholders, {})


if __name__ == '__main__':
    unittest.main()
