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
from solve_it_library.models import Technique, Weakness, Mitigation, Objective
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
        stem = fp.stem  # e.g. "T1001"

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

        # Empty name
        if not (data.get("name") or "").strip():
            result.fail(f"{fp.name} has empty/missing name")

        items[item_id] = data

    result.pass_(f"Loaded {len(items)} {label}", verbose)
    return items


def phase1_data_loading(
    project_root: Path, result: ValidationResult, verbose: bool
) -> Tuple[Dict, Dict, Dict, List[Dict]]:
    """Load all data and return (techniques, weaknesses, mitigations, objectives)."""

    data_dir = project_root / "data"

    techniques = _load_items(data_dir / "techniques", Technique, "techniques", result, verbose)
    weaknesses = _load_items(data_dir / "weaknesses", Weakness, "weaknesses", result, verbose)
    mitigations = _load_items(data_dir / "mitigations", Mitigation, "mitigations", result, verbose)

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

    return techniques, weaknesses, mitigations, objectives


# ── Phase 2: Cross-reference integrity ────────────────────────────────────────

def phase2_cross_references(
    techniques: Dict, weaknesses: Dict, mitigations: Dict, objectives: List[Dict],
    result: ValidationResult, verbose: bool,
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
                    result.fail(f"Technique {tid} {field_name}: \"{url}\" is not a valid URL")
                    bad += 1
                elif not any(url.startswith(prefix) for prefix in KNOWN_PREFIXES):
                    result.fail(
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

    # Summary statistics
    total = len(techniques)
    has_weaknesses = sum(1 for t in techniques.values() if t.get("weaknesses"))
    has_description = sum(1 for t in techniques.values() if (t.get("description") or "").strip())
    has_case = sum(
        1 for t in techniques.values()
        if t.get("CASE_input_classes") or t.get("CASE_output_classes")
    )
    result.pass_(
        f"Completeness stats: {total} techniques, "
        f"{has_description} with description, "
        f"{has_weaknesses} with weaknesses, "
        f"{has_case} with CASE classes",
        verbose=True,  # always show stats
    )


# ── Phase 6: Generator smoke tests ───────────────────────────────────────────

GENERATORS = [
    ("stat_summary", ["python", "reporting_scripts/generate_stat_summary.py"], False),
    ("tsv (techniques)", ["python", "reporting_scripts/generate_tsv_from_kb.py", "-t"], False),
    ("tsv (weaknesses)", ["python", "reporting_scripts/generate_tsv_from_kb.py", "-w"], False),
    ("tsv (mitigations)", ["python", "reporting_scripts/generate_tsv_from_kb.py", "-m"], False),
    ("tsv (objectives)", ["python", "reporting_scripts/generate_tsv_from_kb.py", "-o"], False),
    ("tsv (CASE mapping)", ["python", "reporting_scripts/generate_tsv_from_kb.py", "-c"], False),
    # Generators that need a temp output path (placeholder {tmp} replaced at runtime)
    ("excel", ["python", "reporting_scripts/generate_excel_from_kb.py", "-o", "{tmp}/test.xlsx"], True),
    ("evaluation", ["python", "reporting_scripts/generate_evaluation.py", "-o", "{tmp}/test_eval.xlsx"], True),
    ("html", ["python", "reporting_scripts/generate_html_from_kb.py", "--local", ".", "--output", "{tmp}/test.html"], True),
    ("rdf", ["python", "reporting_scripts/generate_rdf_from_kb.py", "--output-dir", "{tmp}", "--format", "both"], True),
    ("markdown", ["python", "reporting_scripts/generate_md_from_kb.py", "-o", "{tmp}/test.md"], True),
]


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
]


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

    print_phase("Phase 1: Data loading")
    techniques, weaknesses, mitigations, objectives = phase1_data_loading(
        PROJECT_ROOT, result, args.verbose
    )

    print_phase("Phase 2: Cross-reference integrity")
    phase2_cross_references(techniques, weaknesses, mitigations, objectives, result, args.verbose)

    print_phase("Phase 3: ASTM error class flags")
    phase3_astm_flags(weaknesses, result, args.verbose)

    print_phase("Phase 4: CASE/UCO class URLs")
    ontology_issues = phase4_case_urls(techniques, result, args.verbose, check_ontology=args.check_ontology)

    print_phase("Phase 5: Completeness warnings")
    phase5_completeness(techniques, weaknesses, mitigations, objectives, result, args.verbose)

    if not args.skip_generators:
        print_phase("Phase 6: Generator smoke tests")
        phase6_generators(PROJECT_ROOT, result, args.verbose)
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
