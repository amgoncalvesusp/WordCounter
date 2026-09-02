"""Term and phrase search engine for analytical corpus."""
import regex
import unicodedata
from typing import Dict, List, Optional, Tuple


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


ALTERNATIVE_SEPARATOR = "|"
WILDCARD = "*"


def _token_pattern(token: str) -> str:
    """Translate one normalized token into a regex; ``*`` matches any ending."""
    return "".join(
        r"\w*" if part == WILDCARD else regex.escape(part)
        for part in regex.split(r"(\*)", token)
        if part
    )


def term_token_patterns(
    term: str, exact: bool = False, strip_accents: bool = True
) -> List[List[str]]:
    """Return the alternatives of ``term`` as lists of per-token regex sources.

    Unquoted terms support ``*`` (matches the rest of a word, so ``climatic*``
    covers climatica/climatico/climaticas) and ``|`` (alternatives counted under
    a single label). Quoted/exact terms are matched literally.
    """
    normalized = normalize(term, strip_accents)
    alternatives = [normalized] if exact else normalized.split(ALTERNATIVE_SEPARATOR)

    out: List[List[str]] = []
    for alternative in alternatives:
        tokens = alternative.split()
        if not tokens:
            continue
        if exact:
            out.append([regex.escape(token) for token in tokens])
        elif any(character.isalnum() for character in alternative):
            # A wildcard-only alternative would match every word in the document.
            out.append([_token_pattern(token) for token in tokens])
    return out


def _term_regex(term: str, exact: bool, strip_accents: bool) -> Optional[str]:
    """Build the full search regex for a term, or None when it matches nothing."""
    alternatives = term_token_patterns(term, exact, strip_accents)
    if not alternatives:
        return None
    body = "|".join(r"\s+".join(tokens) for tokens in alternatives)
    return r"\b(?:" + body + r")\b"


def count_term(
    text: str, term: str, exact: bool = False, strip_accents: bool = True
) -> int:
    """Count occurrences of term in text with word boundaries."""
    if not text or not term:
        return 0

    pattern = _term_regex(term, exact, strip_accents)
    if pattern is None:
        return 0

    return len(regex.findall(pattern, normalize(text, strip_accents)))


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
