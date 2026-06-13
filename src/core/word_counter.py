"""Word counting engine per ChatGPT prompt specification."""

import regex
from typing import List

WORD_PATTERN = regex.compile(r"\p{L}+(?:[-‐-―]\p{L}+)*", regex.UNICODE)
ROMAN_NUMERAL = regex.compile(
    r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
)
VALID_SINGLE_CHARS = {"a", "e", "o", "y", "i", "u"}


def tokenize(text: str) -> List[str]:
    """Return the list of valid word tokens (same criteria as count_words)."""
    if not text:
        return []
    return [
        m.group(0) for m in WORD_PATTERN.finditer(text) if _is_valid_word(m.group(0))
    ]


def count_words(text: str) -> int:
    return len(tokenize(text))


def _is_valid_word(token: str) -> bool:
    if not token:
        return False
    if len(token) == 1:
        return token.lower() in VALID_SINGLE_CHARS
    if token.isupper() and ROMAN_NUMERAL.match(token):
        return False
    return True


def count_total(pages_text: List[str]) -> int:
    return sum(count_words(t) for t in pages_text)
