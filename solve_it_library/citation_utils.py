"""
Utility functions for citation formatting in the SOLVE-IT Knowledge Base.

Provides Harvard-style reference formatting from BibTeX entries via pybtex,
with plaintext fallback for citations without BibTeX.
"""

import re
from typing import Callable, Dict, List, Optional, Set

from pybtex.database import parse_string


def bibtex_to_harvard(bibtex_str: str) -> Optional[str]:
    """Parse a BibTeX string and format as a Harvard-style reference.

    Uses pybtex to parse the BibTeX entry and manually formats the output
    as Harvard style (pybtex's built-in styles produce LaTeX output).

    Returns None if parsing fails.
    """
    try:
        bib_data = parse_string(bibtex_str, "bibtex")
    except Exception:
        return None

    if not bib_data.entries:
        return None

    entry = list(bib_data.entries.values())[0]
    fields = entry.fields

    # Format authors
    authors_list = []
    if "author" in entry.persons:
        for person in entry.persons["author"]:
            last = " ".join(person.last_names)
            firsts = " ".join(
                f"{n[0]}." if n else "" for n in person.first_names
            )
            if firsts:
                authors_list.append(f"{last}, {firsts}")
            else:
                authors_list.append(last)

    if len(authors_list) == 0:
        author_str = "Unknown"
    elif len(authors_list) == 1:
        author_str = authors_list[0]
    elif len(authors_list) == 2:
        author_str = f"{authors_list[0]} and {authors_list[1]}"
    else:
        author_str = ", ".join(authors_list[:-1]) + f" and {authors_list[-1]}"

    year = fields.get("year", "n.d.")
    title = fields.get("title", "").strip("{}").replace("\\_", "_")
    journal = fields.get("journal", "")
    volume = fields.get("volume", "")
    number = fields.get("number", "")
    pages = fields.get("pages", "")
    publisher = fields.get("publisher", "")
    booktitle = fields.get("booktitle", "")
    url = fields.get("url", "")

    # Build Harvard format — avoid double period if year already ends with one
    year_sep = "." if not year.endswith(".") else ""
    parts = [f"{author_str}, {year}{year_sep} {title}."]

    if journal:
        journal_part = f" {journal}"
        if volume:
            journal_part += f", {volume}"
            if number:
                journal_part += f"({number})"
        if pages:
            journal_part += f", pp.{pages}"
        journal_part += "."
        parts.append(journal_part)
    elif booktitle:
        bt_part = f" In: {booktitle}"
        if pages:
            bt_part += f", pp.{pages}"
        bt_part += "."
        parts.append(bt_part)

    if publisher:
        parts.append(f" {publisher}.")

    if url:
        parts.append(f" Available at: {url}")

    return "".join(parts)


def get_display_text(citation: dict) -> str:
    """Get the best display text for a citation.

    Tries Harvard formatting from BibTeX first, falls back to plaintext.

    Args:
        citation: A citation dict with optional 'bibtex' and/or 'plaintext' keys.

    Returns:
        The formatted display text string.
    """
    bibtex = citation.get("bibtex")
    if bibtex:
        harvard = bibtex_to_harvard(bibtex)
        if harvard:
            return harvard
    return citation.get("plaintext") or ""


# ── Inline citation support ──────────────────────────────────────────────────

# Matches [DFCite-1234] markers in text
INLINE_CITE_RE = re.compile(r"\[DFCite-\d+\]")


def extract_short_form(plaintext: str) -> str:
    """Extract a short Harvard-style in-text citation from a plaintext reference.

    Attempts to parse "Author, ..., YEAR. Title..." and produce
    "(Author et al., YEAR)" or "(Author and Other, YEAR)" or "(Author, YEAR)".

    Falls back to the DFCite ID if parsing fails.
    """
    if not plaintext:
        return ""

    # Try to extract year — look for a 4-digit year
    year_match = re.search(r"\b(1[89]\d{2}|20[0-3]\d)\b", plaintext)
    year = year_match.group(1) if year_match else None

    # Try to extract first author surname — text before first comma
    first_comma = plaintext.find(",")
    if first_comma > 0:
        first_author = plaintext[:first_comma].strip()
    else:
        first_author = None

    if not first_author or not year:
        return ""

    # Count authors by splitting on " and " before the year
    text_before_year = plaintext[:year_match.start()] if year_match else plaintext

    # Split on " and " to find author groups
    # In Harvard format: "Surname, I., Surname, I. and Surname, I., YEAR."
    # Each author takes the form "Surname, I." so we count authors by
    # splitting on " and " and then counting surname-initial pairs
    and_parts = text_before_year.split(" and ")

    if len(and_parts) == 1:
        # No "and" — single author
        return f"({first_author}, {year})"

    # Count authors before "and" by looking for initial patterns (X.)
    # Each "Surname, X." or "Surname, X.X." is one author
    before_and = and_parts[0]
    # Count author entries: each initial block like "V." or "G.J." = one author
    author_entries = re.findall(r"[A-Z]\.(?:[A-Z]\.)*", before_and)
    num_authors_before_and = max(len(author_entries), 1)
    total_authors = num_authors_before_and + 1  # +1 for the author after "and"

    if total_authors >= 3:
        return f"({first_author} et al., {year})"
    elif total_authors == 2:
        # Get second author's surname
        after_and = and_parts[-1].strip()
        second_comma = after_and.find(",")
        second_author = after_and[:second_comma].strip() if second_comma > 0 else after_and.strip()
        return f"({first_author} and {second_author}, {year})"
    else:
        return f"({first_author}, {year})"


def find_inline_citations(text: str) -> List[str]:
    """Find all [DFCite-xxxx] markers in a text string.

    Returns a list of citation IDs (e.g. ["DFCite-1115", "DFCite-1042"]).
    """
    return [m[1:-1] for m in INLINE_CITE_RE.findall(text)]


def resolve_inline_citations(
    text: str,
    citations: Dict[str, dict],
    formatter: Optional[Callable[[str, dict], str]] = None,
) -> str:
    """Replace [DFCite-xxxx] markers with formatted citation text.

    Args:
        text: The text containing [DFCite-xxxx] markers.
        citations: Dict mapping citation IDs to citation dicts.
        formatter: Optional function(cite_id, citation_dict) -> replacement string.
                   If None, uses the short Harvard form e.g. "(Roussev et al., 2013)".

    Returns:
        The text with markers replaced.
    """
    def _default_format(cite_id: str, citation: dict) -> str:
        short = extract_short_form(citation.get("plaintext", ""))
        return short if short else f"({cite_id})"

    fmt = formatter or _default_format

    def _replace(match: re.Match) -> str:
        cite_id = match.group(0)[1:-1]  # strip [ and ]
        citation = citations.get(cite_id)
        if citation is None:
            return match.group(0)  # leave as-is if not found
        return fmt(cite_id, citation)

    return INLINE_CITE_RE.sub(_replace, text)
