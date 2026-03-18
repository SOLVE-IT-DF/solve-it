#!/usr/bin/env python3
"""
SOLVE-IT Knowledge Base Validator

Runs structured validation checks across the entire knowledge base with
clear pass/fail/warn output. Returns exit code 1 if any FAILs are found.

Usage:
    python admin/validate_kb.py [--skip-generators] [--verbose]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import ValidationError
from solve_it_library.models import Technique, Weakness, Mitigation, Objective, CitationFiles
from solve_it_library.citation_utils import find_inline_citations
from solve_it_library.ontology_utils import OntologyLookup, SOLVEIT_ONTOLOGY_DEFAULT_URL


# ── Output helpers ────────────────────────────────────────────────────────────

class ValidationResult:
    """Tracks pass/fail/warn counts and messages."""

    def __init__(self):
        self.passes: List[str] = []
        self.fails: List[str] = []
        self.warnings: List[str] = []

    def pass_(self, msg: str, verbose: bool = False):
        self.passes.append(msg)
        if verbose:
            print(f"  [PASS]  {msg}")

    def fail(self, msg: str):
        self.fails.append(msg)
        print(f"  [FAIL]  {msg}")

    def warn(self, msg: str):
        self.warnings.append(msg)
        print(f"  [WARN]  {msg}")

    @property
    def ok(self) -> bool:
        return len(self.fails) == 0


def print_phase(title: str):
    width = 60
    pad = width - len(title) - 2  # 2 for spaces around title
    print(f"\n\u2550\u2550 {title} " + "\u2550" * max(pad, 2))


def print_summary(result: ValidationResult):
    print_phase("Summary")
    p = len(result.passes)
    f = len(result.fails)
    w = len(result.warnings)
    print(f"  Passed: {p}   Failed: {f}   Warnings: {w}")
    if result.ok:
        print("\n  All checks passed.")
    else:
        print(f"\n  {f} check(s) FAILED — see details above.")


# ── Phase 1: Data loading & file integrity ────────────────────────────────────

def _valid_json_keys(model_class) -> set:
    """Return the set of JSON key names accepted by a Pydantic model."""
    keys = set()
    for field_name, field_info in model_class.model_fields.items():
        keys.add(field_name)
        if field_info.alias:
            keys.add(field_info.alias)
    return keys


def _load_items(directory: Path, model_class, label: str, result: ValidationResult, verbose: bool):
    """Load and validate all JSON files in a directory against a Pydantic model.

    Returns a dict of id -> parsed dict (from JSON), and the set of loaded IDs.
    """
    items: Dict[str, Dict[str, Any]] = {}
    seen_ids: Dict[str, str] = {}  # id -> filename
    json_files = sorted(directory.glob("*.json"))
    valid_keys = _valid_json_keys(model_class)

    if not json_files:
        result.fail(f"No JSON files found in {directory}")
        return items

    for fp in json_files:
        stem = fp.stem  # e.g. "DFT-1001"

        # Try JSON parse
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            result.fail(f"Malformed JSON in {fp.name}: {exc}")
            continue

        # Pydantic validation
        try:
            model_class(**data)
        except ValidationError as exc:
            result.fail(f"Validation error in {fp.name}: {exc}")
            continue

        item_id = data.get("id", "")

        # Filename / ID match
        if stem != item_id:
            result.fail(f"Filename/ID mismatch: {fp.name} contains id \"{item_id}\"")

        # Duplicate ID check
        if item_id in seen_ids:
            result.fail(f"Duplicate ID {item_id} in {fp.name} (also in {seen_ids[item_id]})")
        else:
            seen_ids[item_id] = fp.name

        # Extra/unknown JSON keys (catches typos like "refernces")
        extra = set(data.keys()) - valid_keys
        for key in sorted(extra):
            result.fail(f"{fp.name} has unknown field \"{key}\" (typo?)")

        # Empty name (skip for models without a name field, e.g. Citation)
        if "name" in valid_keys and not (data.get("name") or "").strip():
            result.fail(f"{fp.name} has empty/missing name")

        items[item_id] = data

    result.pass_(f"Loaded {len(items)} {label}", verbose)
    return items


def phase1_data_loading(
    project_root: Path, result: ValidationResult, verbose: bool
) -> Tuple[Dict, Dict, Dict, List[Dict], Dict]:
    """Load all data and return (techniques, weaknesses, mitigations, objectives, citations)."""

    data_dir = project_root / "data"

    techniques = _load_items(data_dir / "techniques", Technique, "techniques", result, verbose)
    weaknesses = _load_items(data_dir / "weaknesses", Weakness, "weaknesses", result, verbose)
    mitigations = _load_items(data_dir / "mitigations", Mitigation, "mitigations", result, verbose)

    # Load citations from .bib/.txt files
    refs_dir = data_dir / "references"
    citations: Dict[str, Dict[str, Any]] = {}
    if refs_dir.exists():
        cite_ids = set()
        for fp in refs_dir.iterdir():
            if fp.name.startswith("DFCite-") and fp.suffix in (".bib", ".txt"):
                cite_ids.add(fp.stem)
        for cite_id in sorted(cite_ids):
            bibtex = None
            plaintext = None
            bib_path = refs_dir / f"{cite_id}.bib"
            txt_path = refs_dir / f"{cite_id}.txt"
            if bib_path.exists():
                bibtex = bib_path.read_text(encoding="utf-8").strip()
            if txt_path.exists():
                plaintext = txt_path.read_text(encoding="utf-8").strip()
            try:
                cf = CitationFiles(cite_id, bibtex=bibtex, plaintext=plaintext)
                citations[cite_id] = {"bibtex": cf.bibtex, "plaintext": cf.plaintext}
            except ValueError as exc:
                result.fail(f"Citation error for {cite_id}: {exc}")
        # Check for stray .json files that should have been migrated
        json_files = list(refs_dir.glob("DFCite-*.json"))
        if json_files:
            result.fail(f"Found {len(json_files)} old-format .json citation files in data/references/ — migrate to .bib/.txt format")
        result.pass_(f"Loaded {len(citations)} citations", verbose)
    else:
        result.warn("No data/references/ directory found")

    # Load solve-it.json objectives
    objectives: List[Dict[str, Any]] = []
    objectives_path = data_dir / "solve-it.json"
    try:
        with open(objectives_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            result.fail("solve-it.json: expected a JSON array of objectives")
        else:
            for i, obj in enumerate(raw):
                try:
                    Objective(**obj)
                    objectives.append(obj)
                except ValidationError as exc:
                    result.fail(f"solve-it.json objective #{i} validation error: {exc}")
            # Duplicate objective names
            seen_names: Dict[str, int] = {}
            for i, obj in enumerate(objectives):
                name = obj.get("name", "")
                if name in seen_names:
                    result.fail(f"solve-it.json: duplicate objective name \"{name}\" (#{seen_names[name]} and #{i})")
                else:
                    seen_names[name] = i

            result.pass_(f"Loaded {len(objectives)} objectives from solve-it.json", verbose)
    except (json.JSONDecodeError, OSError) as exc:
        result.fail(f"Failed to load solve-it.json: {exc}")

    return techniques, weaknesses, mitigations, objectives, citations


# ── Phase 1b: Deprecated ID format check ─────────────────────────────────────

# Old-format IDs: T/W/M followed by digits (e.g. T1001, W1006, M1027).
# New-format IDs: DFT-/DFW-/DFM- followed by digits (e.g. DFT-1001).
_OLD_ID_PATTERNS = {
    "techniques": re.compile(r'^T\d+(\.\d+)?$'),
    "weaknesses": re.compile(r'^W\d+$'),
    "mitigations": re.compile(r'^M\d+$'),
}

_OLD_FILENAME_PATTERNS = {
    "techniques": re.compile(r'^T\d+(\.\d+)?\.json$'),
    "weaknesses": re.compile(r'^W\d+\.json$'),
    "mitigations": re.compile(r'^M\d+\.json$'),
}

# Fields that contain IDs (value or list-of-values) which should use the new format.
_ID_FIELDS_BY_TYPE = {
    "techniques": {"id": "technique", "weaknesses": "weakness", "subtechniques": "technique"},
    "weaknesses": {"id": "weakness", "mitigations": "mitigation"},
    "mitigations": {"id": "mitigation", "technique": "technique"},
}

# Quick lookup: given a value type, which old-format pattern applies?
_OLD_VALUE_PATTERNS = {
    "technique": re.compile(r'^T\d+(\.\d+)?$'),
    "weakness": re.compile(r'^W\d+$'),
    "mitigation": re.compile(r'^M\d+$'),
}

_NEW_PREFIX_HINT = {
    "technique": "DFT-",
    "weakness": "DFW-",
    "mitigation": "DFM-",
}


def phase1b_deprecated_ids(
    project_root: Path,
    techniques: Dict, weaknesses: Dict, mitigations: Dict, objectives: List[Dict],
    result: ValidationResult, verbose: bool,
):
    """Check for old-format (T/W/M) IDs in filenames, JSON id fields, and cross-references."""
    data_dir = project_root / "data"
    bad = 0

    # 1. Check filenames
    for subdir, pattern in _OLD_FILENAME_PATTERNS.items():
        directory = data_dir / subdir
        if not directory.exists():
            continue
        for fp in sorted(directory.glob("*.json")):
            if pattern.match(fp.name):
                if subdir == "techniques":
                    new_name = "DFT-" + fp.name[1:]
                elif subdir == "weaknesses":
                    new_name = "DFW-" + fp.name[1:]
                else:
                    new_name = "DFM-" + fp.name[1:]
                result.fail(
                    f"Deprecated filename {fp.name} uses old ID scheme — "
                    f"rename to {new_name}"
                )
                bad += 1

    # 2. Check ID fields inside loaded items
    for items, item_type in [
        (techniques, "techniques"),
        (weaknesses, "weaknesses"),
        (mitigations, "mitigations"),
    ]:
        field_map = _ID_FIELDS_BY_TYPE[item_type]
        for item_id, data in items.items():
            for field_name, value_type in field_map.items():
                old_pat = _OLD_VALUE_PATTERNS[value_type]
                hint = _NEW_PREFIX_HINT[value_type]
                values = data.get(field_name)
                if values is None:
                    continue
                if isinstance(values, str):
                    values = [values]
                for val in values:
                    if old_pat.match(val):
                        result.fail(
                            f"{item_id} field \"{field_name}\" contains deprecated ID "
                            f"\"{val}\" — use \"{hint}\" prefix instead (e.g. {hint}{val[1:]})"
                        )
                        bad += 1

    # 3. Check technique IDs in objectives (solve-it.json)
    old_tech_pat = _OLD_VALUE_PATTERNS["technique"]
    for obj in objectives:
        obj_name = obj.get("name", "?")
        for tid in obj.get("techniques", []):
            if old_tech_pat.match(tid):
                result.fail(
                    f"Objective \"{obj_name}\" contains deprecated technique ID "
                    f"\"{tid}\" — use DFT-{tid[1:]} instead"
                )
                bad += 1

    if bad == 0:
        result.pass_("No deprecated (T/W/M) IDs found — all use DFT-/DFW-/DFM- format", verbose)

    # Check for old-format references (plain strings or list tuples instead of dicts)
    old_ref_bad = 0
    for items, label in [
        (techniques, "technique"),
        (weaknesses, "weakness"),
        (mitigations, "mitigation"),
    ]:
        for item_id, data in items.items():
            for ref in data.get("references", []):
                if isinstance(ref, str):
                    result.fail(
                        f"{item_id} has old-format reference (plain string instead of "
                        f"{{DFCite_id, relevance_summary_280}} dict): \"{ref[:80]}\""
                    )
                    old_ref_bad += 1
                elif isinstance(ref, list):
                    result.fail(
                        f"{item_id} has old-format reference (list instead of "
                        f"{{DFCite_id, relevance_summary_280}} dict): {ref!r}"
                    )
                    old_ref_bad += 1
    # Also check objectives
    for obj in objectives:
        for ref in obj.get("references", []):
            if isinstance(ref, str):
                result.fail(
                    f"Objective \"{obj.get('name', '?')}\" has old-format reference (plain string): \"{ref[:80]}\""
                )
                old_ref_bad += 1
            elif isinstance(ref, list):
                result.fail(
                    f"Objective \"{obj.get('name', '?')}\" has old-format reference (list): {ref!r}"
                )
                old_ref_bad += 1
    if old_ref_bad == 0:
        result.pass_("No old-format references found — all use {DFCite_id, relevance_summary_280} dicts", verbose)


# ── Phase 2: Cross-reference integrity ────────────────────────────────────────

def phase2_cross_references(
    techniques: Dict, weaknesses: Dict, mitigations: Dict, objectives: List[Dict],
    result: ValidationResult, verbose: bool,
    citations: Optional[Dict] = None,
):
    tech_ids = set(techniques.keys())
    weak_ids = set(weaknesses.keys())
    mit_ids = set(mitigations.keys())

    # technique.weaknesses -> weaknesses
    bad = 0
    for tid, t in techniques.items():
        for wid in t.get("weaknesses", []):
            if wid not in weak_ids:
                result.fail(f"Technique {tid} references non-existent weakness {wid}")
                bad += 1
    if bad == 0:
        result.pass_("All technique -> weakness references valid", verbose)

    # technique.subtechniques -> techniques
    bad = 0
    for tid, t in techniques.items():
        for sid in t.get("subtechniques", []):
            if sid not in tech_ids:
                result.fail(f"Technique {tid} references non-existent subtechnique {sid}")
                bad += 1
    if bad == 0:
        result.pass_("All technique -> subtechnique references valid", verbose)

    # weakness.mitigations -> mitigations
    bad = 0
    for wid, w in weaknesses.items():
        for mid in w.get("mitigations", []):
            if mid not in mit_ids:
                result.fail(f"Weakness {wid} references non-existent mitigation {mid}")
                bad += 1
    if bad == 0:
        result.pass_("All weakness -> mitigation references valid", verbose)

    # objective.techniques -> techniques
    bad = 0
    for obj in objectives:
        for tid in obj.get("techniques", []):
            if tid not in tech_ids:
                result.fail(f"Objective \"{obj.get('name', '?')}\" references non-existent technique {tid}")
                bad += 1
    if bad == 0:
        result.pass_("All objective -> technique references valid", verbose)

    # mitigation.technique -> techniques
    bad = 0
    for mid, m in mitigations.items():
        ref = m.get("technique")
        if ref and ref not in tech_ids:
            result.fail(f"Mitigation {mid} references non-existent technique {ref}")
            bad += 1
    if bad == 0:
        result.pass_("All mitigation -> technique references valid", verbose)

    # Duplicate references within a single item
    bad = 0
    for tid, t in techniques.items():
        for field in ("weaknesses", "subtechniques"):
            refs = t.get(field, [])
            if len(refs) != len(set(refs)):
                dupes = [r for r in refs if refs.count(r) > 1]
                result.fail(f"Technique {tid} has duplicate entries in {field}: {sorted(set(dupes))}")
                bad += 1
    for wid, w in weaknesses.items():
        refs = w.get("mitigations", [])
        if len(refs) != len(set(refs)):
            dupes = [r for r in refs if refs.count(r) > 1]
            result.fail(f"Weakness {wid} has duplicate entries in mitigations: {sorted(set(dupes))}")
            bad += 1
    if bad == 0:
        result.pass_("No duplicate references within items", verbose)

    # Self-referencing subtechniques
    bad = 0
    for tid, t in techniques.items():
        if tid in t.get("subtechniques", []):
            result.fail(f"Technique {tid} lists itself as a subtechnique")
            bad += 1
    if bad == 0:
        result.pass_("No self-referencing subtechniques", verbose)

    # Duplicate techniques within objectives
    bad = 0
    for obj in objectives:
        refs = obj.get("techniques", [])
        if len(refs) != len(set(refs)):
            dupes = [r for r in refs if refs.count(r) > 1]
            result.fail(f"Objective \"{obj.get('name', '?')}\" has duplicate techniques: {sorted(set(dupes))}")
            bad += 1
    if bad == 0:
        result.pass_("No duplicate techniques within objectives", verbose)

    # Techniques appearing in more than one objective
    tech_to_objs: Dict[str, list] = {}
    for obj in objectives:
        for tid in obj.get("techniques", []):
            tech_to_objs.setdefault(tid, []).append(obj.get("id", "?"))
    multi = {tid: objs for tid, objs in tech_to_objs.items() if len(objs) > 1}
    if multi:
        for tid, objs in sorted(multi.items()):
            result.warn(f"Technique {tid} appears in multiple objectives: {', '.join(objs)}")
    else:
        result.pass_("No techniques shared across objectives", verbose)

    # Citation cross-reference check
    if citations is not None:
        citation_ids = set(citations.keys())
        bad = 0
        for items, label in [
            (techniques, "Technique"),
            (weaknesses, "Weakness"),
            (mitigations, "Mitigation"),
        ]:
            for item_id, data in items.items():
                for ref in data.get("references", []):
                    if isinstance(ref, dict) and "DFCite_id" in ref:
                        cite_id = ref["DFCite_id"]
                        if cite_id not in citation_ids:
                            result.fail(f"{label} {item_id} references non-existent citation {cite_id}")
                            bad += 1
        for obj in objectives:
            for ref in obj.get("references", []):
                if isinstance(ref, dict) and "DFCite_id" in ref:
                    cite_id = ref["DFCite_id"]
                    if cite_id not in citation_ids:
                        result.fail(f"Objective \"{obj.get('name', '?')}\" references non-existent citation {cite_id}")
                        bad += 1
        if bad == 0:
            result.pass_("All citation references (DFCite-xxxx) exist in data/references/", verbose)

        # Inline citation check: [DFCite-xxxx] markers in text fields
        inline_bad = 0
        text_fields = ["description", "details", "name"]
        for items, label in [
            (techniques, "Technique"),
            (weaknesses, "Weakness"),
            (mitigations, "Mitigation"),
        ]:
            for item_id, data in items.items():
                for field in text_fields:
                    text = data.get(field, "") or ""
                    for cite_id in find_inline_citations(text):
                        if cite_id not in citation_ids:
                            result.fail(f"{label} {item_id} field \"{field}\" has inline citation [{cite_id}] that does not exist")
                            inline_bad += 1
        if inline_bad == 0:
            result.pass_("All inline [DFCite-xxxx] citations in text fields exist in data/references/", verbose)


# ── Phase 3: ASTM error class flags ──────────────────────────────────────────

ASTM_FIELDS = ["INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT"]
VALID_FLAG_VALUES = {None, "", "x", "X"}


def phase3_astm_flags(weaknesses: Dict, result: ValidationResult, verbose: bool):
    bad = 0
    for wid, w in weaknesses.items():
        for field in ASTM_FIELDS:
            val = w.get(field)
            if val not in VALID_FLAG_VALUES:
                result.fail(f"Weakness {wid} has invalid ASTM flag {field}=\"{val}\" (expected blank, \"x\", or \"X\")")
                bad += 1
    if bad == 0:
        result.pass_("All ASTM error class flags are valid", verbose)


# ── Phase 4: CASE/UCO class URLs ─────────────────────────────────────────────

KNOWN_PREFIXES = [
    "https://ontology.unifiedcyberontology.org/uco/",
    "https://ontology.caseontology.org/case/",
    "https://ontology.solveit-df.org/solveit/",
    "https://cacontology.projectvic.org/",
]

URL_PATTERN = re.compile(r"^https?://")


PROJECTVIC_ONTOLOGY_BASE = (
    "https://raw.githubusercontent.com/Project-VIC-International/CAC-Ontology/main/ontology/"
)


def _get_projectvic_ttl_urls() -> List[str]:
    """Fetch the list of non-shape TTL files from the ProjectVic CAC-Ontology repo."""
    api_url = "https://api.github.com/repos/Project-VIC-International/CAC-Ontology/contents/ontology"
    try:
        try:
            import requests
            resp = requests.get(api_url, headers={"Accept": "application/vnd.github.v3+json"}, timeout=15)
            resp.raise_for_status()
            entries = resp.json()
        except ImportError:
            import urllib.request
            req = urllib.request.Request(api_url, headers={"Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                entries = json.loads(resp.read())
        return [
            PROJECTVIC_ONTOLOGY_BASE + e["name"]
            for e in entries
            if e["name"].endswith(".ttl") and "shapes" not in e["name"]
        ]
    except Exception:
        return []


def phase4_case_urls(techniques: Dict, result: ValidationResult, verbose: bool,
                     check_ontology: bool = False) -> List[str]:
    """Validate CASE/UCO class URLs. Returns list of ontology IRI mismatch messages."""
    bad = 0
    for tid, t in techniques.items():
        for field_name in ("CASE_input_classes", "CASE_output_classes"):
            for url in t.get(field_name, []):
                if not URL_PATTERN.match(url):
                    result.warn(f"Technique {tid} {field_name}: \"{url}\" is not a valid URL")
                    bad += 1
                elif not any(url.startswith(prefix) for prefix in KNOWN_PREFIXES):
                    result.warn(
                        f"Technique {tid} {field_name}: \"{url}\" does not match "
                        f"any known ontology prefix"
                    )
                    bad += 1
    if bad == 0:
        result.pass_("All CASE/UCO class URLs are valid", verbose)

    ontology_issues: List[str] = []

    if not check_ontology:
        return ontology_issues

    # Load ontologies and verify each IRI exists as a class
    print("  ...loading ontologies (cached after first run)")
    try:
        lookup = OntologyLookup(
            solve_it_ontology_url=SOLVEIT_ONTOLOGY_DEFAULT_URL,
            load_case_uco=True,
        )
        # Load additional UCO modules referenced by the KB
        extra_modules = [
            "https://raw.githubusercontent.com/ucoProject/UCO/1.4.0/ontology/uco/configuration/configuration.ttl",
            "https://raw.githubusercontent.com/ucoProject/UCO/1.4.0/ontology/uco/identity/identity.ttl",
            "https://raw.githubusercontent.com/ucoProject/UCO/1.4.0/ontology/uco/location/location.ttl",
        ]
        lookup._load_remote_modules(extra_modules)

        # Load all ProjectVic CAC Ontology modules (excluding SHACL shapes)
        projectvic_modules = _get_projectvic_ttl_urls()
        if projectvic_modules:
            lookup._load_remote_modules(projectvic_modules)
        else:
            result.warn("Could not fetch ProjectVic ontology file list — ProjectVic IRIs will not be verified")
    except Exception as exc:
        result.warn(f"Failed to load ontologies for class verification: {exc}")
        return ontology_issues

    bad = 0
    for tid, t in techniques.items():
        for field_name in ("CASE_input_classes", "CASE_output_classes"):
            for url in t.get(field_name, []):
                desc = lookup.describe_class(url)
                if not desc["found"]:
                    msg = f"Technique {tid} {field_name}: \"{url}\" not found in loaded ontologies"
                    result.warn(msg)
                    ontology_issues.append(msg)
                    bad += 1
    if bad == 0:
        result.pass_("All CASE/UCO class IRIs exist in loaded ontologies", verbose)

    return ontology_issues


# ── Phase 5: Completeness warnings ───────────────────────────────────────────

def phase5_completeness(
    techniques: Dict, weaknesses: Dict, mitigations: Dict, objectives: List[Dict],
    result: ValidationResult, verbose: bool,
    citations: Optional[Dict] = None,
):
    # Techniques with empty/missing description
    for tid, t in techniques.items():
        desc = t.get("description", "")
        if not desc or not desc.strip():
            result.warn(f"Technique {tid} has empty/missing description")

    # Techniques with zero weaknesses
    for tid, t in techniques.items():
        if not t.get("weaknesses"):
            result.warn(f"Technique {tid} has no weaknesses")

    # Weaknesses with zero mitigations
    for tid, w in weaknesses.items():
        if not w.get("mitigations"):
            result.warn(f"Weakness {tid} has no mitigations")

    # Orphaned weaknesses (not referenced by any technique)
    referenced_weaknesses = set()
    for t in techniques.values():
        referenced_weaknesses.update(t.get("weaknesses", []))
    for wid in weaknesses:
        if wid not in referenced_weaknesses:
            result.warn(f"Unreferenced weakness {wid} (not in any technique's weakness list)")

    # Orphaned mitigations (not referenced by any weakness)
    referenced_mitigations = set()
    for w in weaknesses.values():
        referenced_mitigations.update(w.get("mitigations", []))
    for mid in mitigations:
        if mid not in referenced_mitigations:
            result.warn(f"Unreferenced mitigation {mid} (not in any weakness's mitigation list)")

    # Fields containing "todo" placeholder values
    _TODO_RE = re.compile(r"\btodo\b", re.IGNORECASE)

    def _check_todo(item_id: str, data: Dict):
        for key, val in data.items():
            if key == "id":
                continue
            if isinstance(val, str) and _TODO_RE.search(val):
                result.warn(f"{item_id} field \"{key}\" contains todo marker")
            elif isinstance(val, list):
                for entry in val:
                    if isinstance(entry, str) and _TODO_RE.search(entry):
                        result.warn(f"{item_id} field \"{key}\" contains todo marker")
                        break

    for tid, t in techniques.items():
        _check_todo(tid, t)
    for wid, w in weaknesses.items():
        _check_todo(wid, w)
    for mid, m in mitigations.items():
        _check_todo(mid, m)

    # Techniques not in any objective (excluding subtechniques)
    objective_techniques = set()
    for obj in objectives:
        objective_techniques.update(obj.get("techniques", []))
    is_subtechnique = set()
    for t in techniques.values():
        is_subtechnique.update(t.get("subtechniques", []))
    for tid in techniques:
        if tid not in objective_techniques and tid not in is_subtechnique:
            result.warn(f"Technique {tid} is not listed in any objective")

    # Citation completeness checks
    if citations is not None:
        # Check relevance_summary_280: warn if empty, fail if > 280 chars
        for items, label in [
            (techniques, "Technique"),
            (weaknesses, "Weakness"),
            (mitigations, "Mitigation"),
        ]:
            for item_id, data in items.items():
                for ref in data.get("references", []):
                    if isinstance(ref, dict) and "DFCite_id" in ref:
                        summary = ref.get("relevance_summary_280", "").strip()
                        if not summary:
                            result.warn(f"{label} {item_id} has empty relevance_summary for {ref['DFCite_id']}")
                        elif len(summary) > 280:
                            result.fail(f"{label} {item_id} has relevance_summary > 280 chars ({len(summary)}) for {ref['DFCite_id']}")

        # Orphaned citations
        referenced_citations = set()
        for items in [techniques, weaknesses, mitigations]:
            for data in items.values():
                for ref in data.get("references", []):
                    if isinstance(ref, dict) and "DFCite_id" in ref:
                        referenced_citations.add(ref["DFCite_id"])
        for obj in objectives:
            for ref in obj.get("references", []):
                if isinstance(ref, dict) and "DFCite_id" in ref:
                    referenced_citations.add(ref["DFCite_id"])

        for cite_id in citations:
            if cite_id not in referenced_citations:
                result.fail(f"Orphaned citation {cite_id} (not referenced by any T/W/M/Objective)")

    # Summary statistics
    total = len(techniques)
    has_weaknesses = sum(1 for t in techniques.values() if t.get("weaknesses"))
    has_description = sum(1 for t in techniques.values() if (t.get("description") or "").strip())
    has_case = sum(
        1 for t in techniques.values()
        if t.get("CASE_input_classes") or t.get("CASE_output_classes")
    )
    citation_count = len(citations) if citations else 0
    result.pass_(
        f"Completeness stats: {total} techniques, "
        f"{has_description} with description, "
        f"{has_weaknesses} with weaknesses, "
        f"{has_case} with CASE classes, "
        f"{citation_count} citations",
        verbose=True,  # always show stats
    )


# ── Phase 6: Generator smoke tests ───────────────────────────────────────────

GENERATORS = [
    ("stat_summary", [sys.executable, "reporting_scripts/generate_stat_summary.py"], False),
    ("tsv (techniques)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-t"], False),
    ("tsv (weaknesses)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-w"], False),
    ("tsv (techniques long)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-t", "-l"], False),
    ("tsv (techniques by obj)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-t2"], False),
    ("tsv (weaknesses)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-w"], False),
    ("tsv (weaknesses long)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-w", "-l"], False),
    ("tsv (mitigations)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-m"], False),
    ("tsv (objectives)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-o"], False),
    ("tsv (CASE mapping)", [sys.executable, "reporting_scripts/generate_tsv_from_kb.py", "-c"], False),
    # Generators that need a temp output path (placeholder {tmp} replaced at runtime)
    ("excel", [sys.executable, "reporting_scripts/generate_excel_from_kb.py", "-o", "{tmp}/test.xlsx"], True),
    ("evaluation", [sys.executable, "reporting_scripts/generate_evaluation.py", "-o", "{tmp}/test_eval.xlsx"], True),
    ("evaluation (specific)", [sys.executable, "reporting_scripts/generate_evaluation.py", "DFT-1012", "DFT-1002", "DFT-1025", "DFT-1042", "-o", "{tmp}/test_eval2.xlsx"], True),

    ("html", [sys.executable, "reporting_scripts/generate_html_from_kb.py", "--local", ".", "--output", "{tmp}/test.html"], True),
    ("html (custom)", [sys.executable, "reporting_scripts/generate_html_from_kb.py", "--local", ".", "--custom", "--output", "{tmp}/test_custom.html"], True),
    ("rdf", [sys.executable, "reporting_scripts/generate_rdf_from_kb.py", "--output-dir", "{tmp}", "--format", "both"], True),
    ("markdown", [sys.executable, "reporting_scripts/generate_md_from_kb.py", "-o", "{tmp}/test.md"], True),
]


def _extract_objective_options(form_text: str) -> List[str]:
    """Extract objective dropdown options from a GitHub issue form YAML.

    Parses the options list under the 'id: objective' dropdown field
    without requiring PyYAML.
    """
    options = []
    in_objective = False
    in_options = False

    for line in form_text.splitlines():
        stripped = line.strip()
        # Detect the objective field by its id
        if stripped == "id: objective":
            in_objective = True
            continue
        # Once inside the objective field, look for options:
        if in_objective and stripped == "options:":
            in_options = True
            continue
        # Collect option lines (- "value" or - value)
        if in_options:
            if stripped.startswith("- "):
                value = stripped[2:].strip().strip('"')
                if value != "Other (specify below)":
                    options.append(value)
            elif stripped and not stripped.startswith("#"):
                # Non-option line means we've left the options block
                break

    return options


def phase5b_form_sync(project_root: Path, objectives: Dict, result: ValidationResult, verbose: bool):
    """Check that issue form objective dropdowns match the KB."""
    kb_objectives = sorted(obj.get("name", "") for obj in objectives)

    forms_with_objectives = [
        "1a_propose-new-technique-form.yml",
        "3_propose-trwm-submission-form.yml",
    ]

    template_dir = project_root / ".github" / "ISSUE_TEMPLATE"

    for form_file in forms_with_objectives:
        form_path = template_dir / form_file
        if not form_path.exists():
            result.warn(f"Form sync: {form_file} not found")
            continue

        form_text = form_path.read_text()
        form_objectives = sorted(_extract_objective_options(form_text))

        if not form_objectives:
            result.warn(f"Form sync: no objective dropdown found in {form_file}")
            continue

        if form_objectives == kb_objectives:
            result.pass_(f"Form sync: {form_file} objectives match KB", verbose)
        else:
            missing_from_form = set(kb_objectives) - set(form_objectives)
            extra_in_form = set(form_objectives) - set(kb_objectives)
            parts = []
            if missing_from_form:
                parts.append(f"missing: {', '.join(sorted(missing_from_form))}")
            if extra_in_form:
                parts.append(f"extra: {', '.join(sorted(extra_in_form))}")
            result.fail(
                f"Form sync: {form_file} objectives out of date — {'; '.join(parts)}. "
                f"Re-run the form generator to fix."
            )


def phase6_generators(project_root: Path, result: ValidationResult, verbose: bool):
    with tempfile.TemporaryDirectory(prefix="solveit_validate_") as tmpdir:
        for name, cmd_template, uses_tmp in GENERATORS:
            cmd = [
                part.replace("{tmp}", tmpdir) if uses_tmp else part
                for part in cmd_template
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if proc.returncode == 0:
                    result.pass_(f"Generator: {name}", verbose)
                else:
                    stderr_snippet = (proc.stderr or "").strip()[:300]
                    result.fail(f"Generator: {name} exited with code {proc.returncode}\n         {stderr_snippet}")
            except subprocess.TimeoutExpired:
                result.fail(f"Generator: {name} timed out after 120s")
            except Exception as exc:
                result.fail(f"Generator: {name} raised {exc}")


# ── Markdown summary ──────────────────────────────────────────────────────────

WARNING_CATEGORIES = [
    ("Empty/missing description", "has empty/missing description"),
    ("No weaknesses", "has no weaknesses"),
    ("No mitigations", "has no mitigations"),
    ("Unreferenced weaknesses", "Unreferenced weakness"),
    ("Unreferenced mitigations", "Unreferenced mitigation"),
    ("Todo markers", "contains todo marker"),
    ("Not in any objective", "is not listed in any objective"),
    ("Ontology IRI not found", "not found in loaded ontologies"),
    ("Empty relevance summary", "has empty relevance_summary"),
]

# Groups for organising pass/fail checks in the summary.
# Each entry: (display_label, pattern_to_match_in_message)
CHECK_GROUPS = [
    ("Data loading", [
        ("Techniques loaded", "Loaded", "techniques"),
        ("Weaknesses loaded", "Loaded", "weaknesses"),
        ("Mitigations loaded", "Loaded", "mitigations"),
        ("Objectives loaded", "Loaded", "objectives"),
    ]),
    ("ID format", [
        ("No deprecated T/W/M IDs", "No deprecated", "T/W/M"),
        ("No old-format references", "No old-format plain-string references"),
    ]),
    ("Cross-reference integrity", [
        ("Technique → weakness refs", "technique -> weakness"),
        ("Technique → subtechnique refs", "technique -> subtechnique"),
        ("Weakness → mitigation refs", "weakness -> mitigation"),
        ("Objective → technique refs", "objective -> technique"),
        ("Mitigation → technique refs", "mitigation -> technique"),
        ("No duplicate references", "No duplicate references"),
        ("No self-referencing subtechniques", "No self-referencing"),
        ("No duplicate techniques in objectives", "No duplicate techniques"),
        ("Citation references valid", "citation references", "DFCite"),
    ]),
    ("Validation checks", [
        ("ASTM error class flags", "ASTM error class"),
        ("CASE/UCO class URLs valid", "class URLs are valid"),
        ("CASE/UCO class IRIs in ontology", "class IRIs exist"),
    ]),
    ("Issue form sync", [
        ("Technique form objectives", "Form sync:", "1a_propose"),
        ("TRWM form objectives", "Form sync:", "3_propose"),
    ]),
    ("Generator builds", [
        ("Statistics summary", "Generator: stat_summary"),
        ("TSV (techniques)", "Generator: tsv (techniques)"),
        ("TSV (weaknesses)", "Generator: tsv (weaknesses)"),
        ("TSV (mitigations)", "Generator: tsv (mitigations)"),
        ("TSV (objectives)", "Generator: tsv (objectives)"),
        ("TSV (CASE mapping)", "Generator: tsv (CASE mapping)"),
        ("Excel workbook", "Generator: excel"),
        ("Evaluation workbook", "Generator: evaluation"),
        ("HTML viewer (custom)", "Generator: html (custom)"),
        ("HTML viewer", "Generator: html"),
        ("RDF/JSON-LD", "Generator: rdf"),
        ("Markdown", "Generator: markdown"),
    ]),
]


def _build_checks_table(result: ValidationResult) -> List[str]:
    """Build a status table showing pass/fail for each check group."""
    all_msgs = {msg: True for msg in result.passes}
    all_msgs.update({msg: False for msg in result.fails})

    lines = []
    for group_name, checks in CHECK_GROUPS:
        group_results = []
        for check in checks:
            label = check[0]
            patterns = check[1:]
            # A check matches if ALL its patterns appear in any single message
            matched = False
            passed = False
            for msg, is_pass in all_msgs.items():
                if all(p.lower() in msg.lower() for p in patterns):
                    matched = True
                    passed = is_pass
                    break
            if matched:
                icon = "&#9989;" if passed else "&#10060;"
                group_results.append(f"| {icon} | {label} |")

        if group_results:
            lines.append(f"| | **{group_name}** |")
            lines.extend(group_results)

    return lines


def _write_markdown_summary(result: ValidationResult, filepath: str):
    p = len(result.passes)
    f = len(result.fails)
    w = len(result.warnings)

    if f == 0:
        status = "passed"
    else:
        status = "failed"

    # Categorise warnings
    categories = []
    for label, pattern in WARNING_CATEGORIES:
        count = sum(1 for msg in result.warnings if pattern in msg)
        if count > 0:
            categories.append((label, count))

    # Find the completeness stats line
    stats_line = ""
    for msg in result.passes:
        if msg.startswith("Completeness stats:"):
            stats_line = msg.replace("Completeness stats: ", "")
            break

    lines = [f"## KB Validation Summary ({status})", ""]

    if f == 0:
        lines.append(f"**{p} checks passed** | **{w} warnings**")
    else:
        lines.append(f"**{p} passed** | **{f} failed** | **{w} warnings**")
        lines.append("")
        lines.append("### Failures")
        lines.append("")
        for msg in result.fails:
            lines.append(f"- {msg}")

    # Checks passed / failed detail
    checks_table = _build_checks_table(result)
    if checks_table:
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Checks detail</summary>")
        lines.append("")
        lines.append("| Status | Check |")
        lines.append("|:------:|-------|")
        lines.extend(checks_table)
        lines.append("")
        lines.append("</details>")

    if categories:
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Warnings breakdown</summary>")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|------:|")
        for label, count in categories:
            lines.append(f"| {label} | {count} |")
        lines.append("")

        # For small categories, list the actual warnings
        for label, pattern in WARNING_CATEGORIES:
            matching = [msg for msg in result.warnings if pattern in msg]
            if 0 < len(matching) <= 5:
                lines.append(f"**{label}:**")
                lines.append("")
                for msg in matching:
                    lines.append(f"- {msg}")
                lines.append("")

        lines.append("</details>")

    if stats_line:
        lines.append("")
        lines.append(f"**Completeness:** {stats_line}")

    with open(filepath, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def _write_ontology_summary(ontology_issues: List[str], filepath: str):
    """Write a separate markdown report for ontology IRI mismatches."""
    if not ontology_issues:
        lines = [
            "## Ontology IRI Check",
            "",
            "All CASE/UCO/SOLVE-IT class IRIs exist in loaded ontologies.",
        ]
    else:
        lines = [
            "## Ontology IRI Check",
            "",
            f"**{len(ontology_issues)} class IRI(s) not found** in the loaded ontologies.",
            "",
            "These IRIs may have been renamed, removed, or not yet published. "
            "This does not block the build but should be investigated.",
            "",
        ]
        for msg in ontology_issues:
            lines.append(f"- {msg}")

    with open(filepath, "w") as fh:
        fh.write("\n".join(lines) + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate the SOLVE-IT knowledge base")
    parser.add_argument(
        "--skip-generators",
        action="store_true",
        help="Skip Phase 6 generator smoke tests (faster local runs)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print details for every check, not just failures/warnings",
    )
    parser.add_argument(
        "--check-ontology",
        action="store_true",
        help="Load SOLVE-IT + CASE/UCO ontologies and verify CASE class IRIs exist (requires network on first run)",
    )
    parser.add_argument(
        "--markdown-summary",
        type=str,
        metavar="FILE",
        help="Write a markdown summary to FILE (for use as a PR comment)",
    )
    parser.add_argument(
        "--ontology-summary",
        type=str,
        metavar="FILE",
        help="Write ontology IRI mismatch report to FILE (for use as a separate PR comment)",
    )
    args = parser.parse_args()

    result = ValidationResult()

    def phase_ok_check(before_fails, before_warns):
        """Print 'all ok' if no new failures or warnings were added."""
        new_fails = len(result.fails) - before_fails
        new_warns = len(result.warnings) - before_warns
        if new_fails == 0 and new_warns == 0:
            print("  [OK]    All checks passed.")

    print_phase("Phase 1: Data loading")
    f0, w0 = len(result.fails), len(result.warnings)
    techniques, weaknesses, mitigations, objectives, citations = phase1_data_loading(
        PROJECT_ROOT, result, args.verbose
    )
    phase_ok_check(f0, w0)

    print_phase("Phase 1b: Deprecated ID format check")
    f0, w0 = len(result.fails), len(result.warnings)
    phase1b_deprecated_ids(
        PROJECT_ROOT, techniques, weaknesses, mitigations, objectives, result, args.verbose
    )
    phase_ok_check(f0, w0)

    print_phase("Phase 2: Cross-reference integrity")
    f0, w0 = len(result.fails), len(result.warnings)
    phase2_cross_references(techniques, weaknesses, mitigations, objectives, result, args.verbose, citations=citations)
    phase_ok_check(f0, w0)

    print_phase("Phase 3: ASTM error class flags")
    f0, w0 = len(result.fails), len(result.warnings)
    phase3_astm_flags(weaknesses, result, args.verbose)
    phase_ok_check(f0, w0)

    print_phase("Phase 4: CASE/UCO class URLs")
    f0, w0 = len(result.fails), len(result.warnings)
    ontology_issues = phase4_case_urls(techniques, result, args.verbose, check_ontology=args.check_ontology)
    phase_ok_check(f0, w0)

    print_phase("Phase 5: Completeness warnings")
    f0, w0 = len(result.fails), len(result.warnings)
    phase5_completeness(techniques, weaknesses, mitigations, objectives, result, args.verbose, citations=citations)
    phase_ok_check(f0, w0)

    print_phase("Phase 5b: Issue form sync")
    f0, w0 = len(result.fails), len(result.warnings)
    phase5b_form_sync(PROJECT_ROOT, objectives, result, args.verbose)
    phase_ok_check(f0, w0)

    if not args.skip_generators:
        print_phase("Phase 6: Generator smoke tests")
        f0, w0 = len(result.fails), len(result.warnings)
        phase6_generators(PROJECT_ROOT, result, args.verbose)
        phase_ok_check(f0, w0)
    else:
        print_phase("Phase 6: Generator smoke tests (SKIPPED)")

    print_summary(result)

    if args.markdown_summary:
        _write_markdown_summary(result, args.markdown_summary)

    if args.ontology_summary:
        _write_ontology_summary(ontology_issues, args.ontology_summary)

    sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
