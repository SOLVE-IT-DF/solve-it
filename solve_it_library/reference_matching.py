"""
Shared reference matching module for issue parsers.

Validates user-submitted DFCite IDs (from GitHub issue forms) against the
existing reference corpus.  Free-text citations are rejected — contributors
must create references separately using the "Propose new reference" form
before referencing them in techniques, weaknesses, or mitigations.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

from solve_it_library.citation_utils import bibtex_to_harvard


# ── Corpus loading ────────────────────────────────────────────────────────────

def load_reference_corpus(project_root: str) -> Dict[str, str]:
    """Read all .txt/.bib files from data/references/ and build a lookup dict.

    Returns:
        dict mapping DFCite_id -> plaintext (Harvard-formatted for .bib-only).
    """
    refs_dir = os.path.join(project_root, "data", "references")
    if not os.path.isdir(refs_dir):
        return {}

    # Collect all DFCite IDs present
    ids = set()
    for fname in os.listdir(refs_dir):
        m = re.match(r"(DFCite-\d+)\.(txt|bib)$", fname)
        if m:
            ids.add(m.group(1))

    corpus: Dict[str, str] = {}
    for cite_id in sorted(ids):
        txt_path = os.path.join(refs_dir, f"{cite_id}.txt")
        bib_path = os.path.join(refs_dir, f"{cite_id}.bib")

        plaintext = ""
        if os.path.isfile(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                plaintext = f.read().strip()

        if not plaintext and os.path.isfile(bib_path):
            with open(bib_path, "r", encoding="utf-8") as f:
                bib_str = f.read()
            harvard = bibtex_to_harvard(bib_str)
            if harvard:
                plaintext = harvard

        if plaintext:
            corpus[cite_id] = plaintext

    return corpus


# ── URL extraction helper ─────────────────────────────────────────────────────

_URL_RE = re.compile(r"https?://[^\s,)>]+")


def _extract_urls(text: str) -> set:
    """Extract URLs from a string."""
    return set(_URL_RE.findall(text))


# ── DOI extraction helper ────────────────────────────────────────────────────

_DOI_PATTERNS = [
    re.compile(r"https?://doi\.org/(10\.\d{4,9}/[^\s,)>]+)"),
    re.compile(r"doi:\s*(10\.\d{4,9}/[^\s,)>]+)", re.IGNORECASE),
    re.compile(r"(?<!\w)(10\.\d{4,9}/[^\s,)>]+)"),
]


def _extract_dois(text: str) -> set:
    """Extract and normalize DOIs from a string.

    Handles:
        - ``https://doi.org/10.XXXX/...`` → ``10.XXXX/...``
        - ``doi: 10.XXXX/...`` → ``10.XXXX/...``
        - Bare ``10.XXXX/...`` → as-is
    """
    dois = set()
    for pattern in _DOI_PATTERNS:
        for m in pattern.finditer(text):
            doi = m.group(1).rstrip(".")
            dois.add(doi.lower())
    return dois


# ── Single-reference matching ─────────────────────────────────────────────────

def match_reference(
    text: str,
    corpus: Dict[str, str],
    prefix_len: int = 60,
) -> Optional[Tuple[str, str]]:
    """Attempt to match a raw citation string against the existing corpus.

    Matching strategies (tried in order):
        1. Direct DFCite ID — text matches ``DFCite-\\d+``
        2. URL overlap — a URL found in both the input and a corpus entry
        3. DOI overlap — a DOI found in both the input and a corpus entry
        4. Prefix match — first *prefix_len* chars match (case-insensitive)

    Returns:
        (DFCite_id, match_type) or None
    """
    stripped = text.strip()
    if not stripped:
        return None

    # 1. Direct DFCite ID
    id_match = re.match(r"^(DFCite-\d{4,6})$", stripped)
    if id_match:
        cite_id = id_match.group(1)
        if cite_id in corpus:
            return (cite_id, "direct_id")
        return None  # ID not found in corpus

    # 2. URL extraction match
    input_urls = _extract_urls(stripped)
    if input_urls:
        for cite_id, corpus_text in corpus.items():
            corpus_urls = _extract_urls(corpus_text)
            if input_urls & corpus_urls:
                return (cite_id, "url")

    # 3. DOI overlap match
    input_dois = _extract_dois(stripped)
    if input_dois:
        for cite_id, corpus_text in corpus.items():
            if input_dois & _extract_dois(corpus_text):
                return (cite_id, "doi")

    # 4. Prefix match (first N chars, case-insensitive)
    input_prefix = stripped[:prefix_len].lower()
    if len(input_prefix) >= 10:  # only attempt if there's enough text
        for cite_id, corpus_text in corpus.items():
            if corpus_text[:prefix_len].lower() == input_prefix:
                return (cite_id, "prefix")

    return None



# ── Batch processing ──────────────────────────────────────────────────────────

_DFCITE_RE = re.compile(r"^DFCite-\d{4,6}$")


def process_reference_lines(
    lines: List[str],
    project_root: str,
) -> Tuple[List[Dict[str, str]], List[str], List[Tuple[str, str]], List[str]]:
    """Process a list of user-submitted reference lines.

    Only DFCite IDs are accepted.  Free-text citations are rejected with a
    message directing the contributor to create the reference first using
    the "Propose new reference" form.

    Args:
        lines: Non-empty reference lines from the issue form.
        project_root: Path to the project root directory.

    Returns:
        processed_refs: List of ``{"DFCite_id": ..., "relevance_summary_280": ""}`` dicts.
        match_report: Human-readable lines for the GitHub comment.
        new_citations: Always empty (kept for API compatibility).
        warnings: List of warning strings for invalid or free-text references.
    """
    corpus = load_reference_corpus(project_root)

    processed_refs: List[Dict[str, str]] = []
    match_report: List[str] = []
    new_citations: List[Tuple[str, str]] = []  # always empty now
    warnings: List[str] = []

    seen_ids = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Split on first pipe to extract optional relevance summary
        if "|" in line:
            ref_part, relevance = line.split("|", 1)
            ref_part = ref_part.strip()
            relevance = relevance.strip()
            if len(relevance) > 280:
                raise ValueError(
                    f"Relevance summary for '{ref_part}' is {len(relevance)} chars "
                    f"(max 280). Please shorten it and resubmit."
                )
        else:
            ref_part = line
            relevance = ""

        if _DFCITE_RE.match(ref_part):
            # User provided a DFCite ID — check it exists
            if ref_part in corpus:
                if ref_part not in seen_ids:
                    processed_refs.append({
                        "DFCite_id": ref_part,
                        "relevance_summary_280": relevance,
                    })
                    seen_ids.add(ref_part)
                report_line = f'- **{ref_part}** found in corpus'
                if relevance:
                    report_line += f' — relevance: "{relevance}"'
                match_report.append(report_line)
            else:
                warnings.append(
                    f'`{ref_part}` was not found in the reference corpus. '
                    f'Please check the ID — it may be a typo. '
                    f'Existing references can be browsed in `data/references/`.'
                )
                match_report.append(f'- :warning: **{ref_part}** not found in corpus (skipped)')
        else:
            # Free-text citation — reject it
            truncated = ref_part[:80] + ("..." if len(ref_part) > 80 else "")
            warnings.append(
                f'Free-text citation not accepted: "{truncated}". '
                f'Please create the reference first using the '
                f'[Propose new reference](https://github.com/SOLVE-IT-DF/solve-it/issues/new?template=1d_propose-new-reference-form.yml) '
                f'form, then use the assigned DFCite ID here.'
            )
            match_report.append(
                f'- :warning: Free-text citation rejected: "{truncated}" — '
                f'please [create the reference first]'
                f'(https://github.com/SOLVE-IT-DF/solve-it/issues/new?template=1d_propose-new-reference-form.yml) '
                f'and use its DFCite ID'
            )

    return processed_refs, match_report, new_citations, warnings
