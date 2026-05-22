"""Term and phrase search engine for analytical corpus."""
import regex
import unicodedata
from typing import Dict, List, Tuple


def parse_terms(raw_input: str) -> List[Tuple[str, bool]]:
    """
    Parse user input into list of (term, exact_match) tuples.

    Rules:
    - One term per line
    - Lines starting with # are ignored (comments)
    - Quotes around a term mark exact phrase match
    """
    terms = []
    for line in raw_input.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = regex.match(r'^"(.+)"$|^\'(.+)\'$', line)
        if m:
            phrase = m.group(1) or m.group(2)
            terms.append((phrase.strip(), True))
        else:
            terms.append((line, False))
    return terms


def normalize(text: str, strip_accents: bool = True) -> str:
    """Lowercase + optional accent removal."""
    text = text.lower()
    if strip_accents:
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
    return text


def count_term(text: str, term: str, exact: bool = False, strip_accents: bool = True) -> int:
    """Count occurrences of term in text with word boundaries."""
    if not text or not term:
        return 0

    norm_text = normalize(text, strip_accents)
    norm_term = normalize(term, strip_accents)

    if exact:
        pattern = r"\b" + regex.escape(norm_term) + r"\b"
    else:
        words = norm_term.split()
        pattern = r"\b" + r"\s+".join(regex.escape(w) for w in words) + r"\b"

    return len(regex.findall(pattern, norm_text, regex.IGNORECASE))


def search_all_terms(
    pages_text: List[str],
    terms: List[Tuple[str, bool]],
    analytical_pages: List[int] = None,
) -> Dict[str, Dict]:
    """Search for all terms across pages, returning total and analytical counts."""
    results = {}
    analytical_set = set(analytical_pages) if analytical_pages is not None else None

    for term, exact in terms:
        label = f'"{term}"' if exact else term
        total_count = 0
        analytical_count = 0
        for i, page_text in enumerate(pages_text):
            c = count_term(page_text, term, exact=exact)
            total_count += c
            if analytical_set is None or (i + 1) in analytical_set:
                analytical_count += c
        results[label] = {
            "total": total_count,
            "analytical": analytical_count,
            "exact": exact,
            "term": term,
        }
    return results
