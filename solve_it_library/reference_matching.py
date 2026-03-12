"""
Shared reference matching module for issue parsers.

Matches user-submitted citation text (from GitHub issue forms) against the
existing DFCite reference corpus, and assigns new DFCite IDs when no match
is found.
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
        3. Prefix match — first *prefix_len* chars match (case-insensitive)

    Returns:
        (DFCite_id, match_type) or None
    """
    stripped = text.strip()
    if not stripped:
        return None

    # 1. Direct DFCite ID
    id_match = re.match(r"^(DFCite-\d+)$", stripped)
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

    # 3. Prefix match (first N chars, case-insensitive)
    input_prefix = stripped[:prefix_len].lower()
    if len(input_prefix) >= 10:  # only attempt if there's enough text
        for cite_id, corpus_text in corpus.items():
            if corpus_text[:prefix_len].lower() == input_prefix:
                return (cite_id, "prefix")

    return None


# ── Next ID assignment ────────────────────────────────────────────────────────

def get_next_dfcite_id(project_root: str) -> str:
    """Scan data/references/ for the highest DFCite ID and return the next one."""
    refs_dir = os.path.join(project_root, "data", "references")
    max_num = 1000  # start from DFCite-1001 if empty

    if os.path.isdir(refs_dir):
        for fname in os.listdir(refs_dir):
            m = re.match(r"DFCite-(\d+)\.", fname)
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num

    return f"DFCite-{max_num + 1}"


def _next_id_after(current_max: int) -> str:
    """Return the next DFCite ID string given a numeric maximum."""
    return f"DFCite-{current_max + 1}"


# ── Batch processing ──────────────────────────────────────────────────────────

_MATCH_TYPE_LABELS = {
    "direct_id": "Direct ID",
    "url": "URL match",
    "prefix": "Prefix match",
}


def process_reference_lines(
    lines: List[str],
    project_root: str,
) -> Tuple[List[Dict[str, str]], List[str], List[Tuple[str, str]]]:
    """Process a list of user-submitted reference lines.

    For each line, attempts to match against the existing corpus.  Unmatched
    lines are assigned new DFCite IDs.

    Args:
        lines: Non-empty reference lines from the issue form.
        project_root: Path to the project root directory.

    Returns:
        processed_refs: List of ``{"DFCite_id": ..., "relevance_summary_280": ""}`` dicts.
        match_report: Human-readable lines for the GitHub comment.
        new_citations: List of ``(DFCite_id, raw_text)`` for newly created references.
    """
    corpus = load_reference_corpus(project_root)

    processed_refs: List[Dict[str, str]] = []
    match_report: List[str] = []
    new_citations: List[Tuple[str, str]] = []

    # Find current max ID for new assignments
    max_num = 1000
    for cite_id in corpus:
        m = re.match(r"DFCite-(\d+)$", cite_id)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num

    seen_ids = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        result = match_reference(line, corpus)

        if result:
            cite_id, match_type = result
            if cite_id not in seen_ids:
                processed_refs.append({
                    "DFCite_id": cite_id,
                    "relevance_summary_280": "",
                })
                seen_ids.add(cite_id)
            label = _MATCH_TYPE_LABELS.get(match_type, match_type)
            truncated = line[:80] + ("..." if len(line) > 80 else "")
            match_report.append(f'- Matched "{truncated}" → **{cite_id}** ({label})')
        else:
            # Assign new DFCite ID
            max_num += 1
            new_id = f"DFCite-{max_num}"
            processed_refs.append({
                "DFCite_id": new_id,
                "relevance_summary_280": "",
            })
            seen_ids.add(new_id)
            new_citations.append((new_id, line))
            truncated = line[:80] + ("..." if len(line) > 80 else "")
            match_report.append(f'- New reference assigned: **{new_id}** for "{truncated}"')

    return processed_refs, match_report, new_citations
