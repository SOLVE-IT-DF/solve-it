"""
Shared reference matching module for issue parsers.

Validates user-submitted DFCite IDs (from GitHub issue forms) against the
existing reference corpus.  Free-text citations are rejected — contributors
must create references separately using the "Propose new reference" form
before referencing them in techniques, weaknesses, or mitigations.
"""

import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, NamedTuple, Optional, Tuple

from pybtex.database import parse_string as _parse_bibtex

from solve_it_library.citation_utils import bibtex_to_harvard


# ── Signature extraction ──────────────────────────────────────────────────────
# A "signature" is a (normalised_title, first_author_surname, year) tuple used
# to compare two references regardless of surface formatting (BibTeX vs
# Harvard plaintext). Title uses similarity; surname + year are exact-match.


class RefSignature(NamedTuple):
    """Normalised signature of a reference used for matching."""
    title: str            # normalised: lowercased, punctuation stripped, whitespace collapsed
    first_author: str     # lowercased surname of first author, or ""
    year: str             # 4-digit year, or ""


_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20[0-4]\d)\b")


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.replace("{", "").replace("}", "").replace("\\", "")
    t = _PUNCT_RE.sub(" ", t.lower())
    t = _WS_RE.sub(" ", t).strip()
    return t


def _signature_from_bibtex(bibtex_str: str) -> Optional[RefSignature]:
    try:
        bib_data = _parse_bibtex(bibtex_str, "bibtex")
    except Exception:
        return None
    if not bib_data.entries:
        return None
    entry = list(bib_data.entries.values())[0]
    fields = entry.fields

    title = _normalize_title(fields.get("title", ""))
    year = (fields.get("year", "") or "").strip()
    ym = _YEAR_RE.search(year)
    year = ym.group(1) if ym else ""

    surname = ""
    persons = entry.persons.get("author") or entry.persons.get("editor") or []
    if persons:
        first = persons[0]
        if first.last_names:
            surname = " ".join(first.last_names).lower().strip()
            surname = _PUNCT_RE.sub("", surname)

    if not title and not surname and not year:
        return None
    return RefSignature(title=title, first_author=surname, year=year)


def _signature_from_plaintext(text: str) -> Optional[RefSignature]:
    if not text:
        return None
    stripped = text.strip()

    ym = _YEAR_RE.search(stripped)
    year = ym.group(1) if ym else ""

    surname = ""
    first_comma = stripped.find(",")
    if first_comma > 0:
        surname = stripped[:first_comma].strip().lower()
        surname = _PUNCT_RE.sub("", surname)

    title = ""
    if ym:
        after_year = stripped[ym.end():].lstrip(".,;: ")
        dot = after_year.find(".")
        title_raw = after_year[:dot] if dot > 0 else after_year
        title = _normalize_title(title_raw)

    if not title and not surname and not year:
        return None
    return RefSignature(title=title, first_author=surname, year=year)


def _extract_signature(text: str) -> Optional[RefSignature]:
    """Extract a signature from either BibTeX (starts with ``@``) or plaintext."""
    if not text:
        return None
    stripped = text.lstrip()
    if stripped.startswith("@"):
        sig = _signature_from_bibtex(stripped)
        if sig is not None:
            return sig
    return _signature_from_plaintext(text)


def load_reference_signatures(project_root: str) -> Dict[str, RefSignature]:
    """Build a DFCite_id → RefSignature lookup.

    Prefers the .bib file when present (more structured), falls back to the
    Harvard plaintext otherwise.
    """
    refs_dir = os.path.join(project_root, "data", "references")
    signatures: Dict[str, RefSignature] = {}
    if not os.path.isdir(refs_dir):
        return signatures

    ids = set()
    for fname in os.listdir(refs_dir):
        m = re.match(r"(DFCite-\d+)\.(txt|bib)$", fname)
        if m:
            ids.add(m.group(1))

    for cite_id in ids:
        bib_path = os.path.join(refs_dir, f"{cite_id}.bib")
        txt_path = os.path.join(refs_dir, f"{cite_id}.txt")
        sig: Optional[RefSignature] = None
        if os.path.isfile(bib_path):
            try:
                with open(bib_path, "r", encoding="utf-8") as f:
                    sig = _signature_from_bibtex(f.read())
            except OSError:
                sig = None
        if sig is None and os.path.isfile(txt_path):
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    sig = _signature_from_plaintext(f.read())
            except OSError:
                sig = None
        if sig is not None:
            signatures[cite_id] = sig
    return signatures


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


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


# ── Signature-based matching (strict + permissive) ────────────────────────────
# Used to link bare-string references in TRWM submissions to existing DFCite
# entries when URL/DOI/prefix matching misses (e.g. BibTeX vs Harvard text
# for the same paper). Strict = silent auto-link; permissive = flag for human.

STRICT_TITLE_SIMILARITY = 0.9
PERMISSIVE_TITLE_SIMILARITY = 0.7


def match_reference_strict(
    text: str,
    corpus: Dict[str, str],
    signatures: Optional[Dict[str, RefSignature]] = None,
) -> Optional[Tuple[str, str]]:
    """High-confidence match — safe for silent auto-link.

    Tries ``match_reference`` first (URL/DOI/ID/prefix). If that misses,
    falls back to signature match requiring: title similarity ≥ 0.9 AND same
    year AND same first-author surname.

    Returns (DFCite_id, match_type) or None.
    """
    primary = match_reference(text, corpus)
    if primary is not None:
        return primary

    if signatures is None:
        return None

    input_sig = _extract_signature(text)
    if input_sig is None or not input_sig.title:
        return None

    best: Optional[Tuple[str, float]] = None
    for cite_id, sig in signatures.items():
        if not sig.title:
            continue
        if input_sig.year and sig.year and input_sig.year != sig.year:
            continue
        if (input_sig.first_author and sig.first_author
                and input_sig.first_author != sig.first_author):
            continue
        score = _title_similarity(input_sig.title, sig.title)
        if score >= STRICT_TITLE_SIMILARITY and (best is None or score > best[1]):
            best = (cite_id, score)

    if best is not None:
        return (best[0], "signature")
    return None


class CandidateMatch(NamedTuple):
    cite_id: str
    score: float
    reason: str  # short human-readable explanation


def find_candidate_matches(
    text: str,
    corpus: Dict[str, str],
    signatures: Optional[Dict[str, RefSignature]] = None,
    limit: int = 5,
) -> List[CandidateMatch]:
    """Permissive match — surfaces possible duplicates for human review.

    Never used for auto-linking. Returns up to *limit* candidates ordered by
    confidence.
    """
    if signatures is None:
        return []
    input_sig = _extract_signature(text)
    if input_sig is None:
        return []

    candidates: List[CandidateMatch] = []
    seen = set()

    # URL/DOI overlap — strong signal even without title
    input_urls = _extract_urls(text)
    input_dois = _extract_dois(text)
    for cite_id, corpus_text in corpus.items():
        if input_urls and (input_urls & _extract_urls(corpus_text)):
            candidates.append(CandidateMatch(cite_id, 1.0, "shared URL"))
            seen.add(cite_id)
        elif input_dois and (input_dois & _extract_dois(corpus_text)):
            candidates.append(CandidateMatch(cite_id, 1.0, "shared DOI"))
            seen.add(cite_id)

    # Signature-based candidates
    for cite_id, sig in signatures.items():
        if cite_id in seen:
            continue
        if not sig.title and not input_sig.title:
            continue
        title_score = _title_similarity(input_sig.title, sig.title) if (input_sig.title and sig.title) else 0.0
        year_match = bool(input_sig.year and sig.year and input_sig.year == sig.year)
        surname_match = bool(
            input_sig.first_author and sig.first_author
            and input_sig.first_author == sig.first_author
        )

        reasons = []
        score = 0.0
        if title_score >= PERMISSIVE_TITLE_SIMILARITY:
            reasons.append(f"title similarity {title_score:.0%}")
            score = max(score, title_score)
        if year_match and surname_match:
            reasons.append("same author + year")
            score = max(score, 0.7)

        if reasons:
            candidates.append(CandidateMatch(cite_id, score, ", ".join(reasons)))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:limit]


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
