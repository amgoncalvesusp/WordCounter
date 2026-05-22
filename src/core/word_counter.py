"""Word counting engine per ChatGPT prompt specification."""
import regex
from typing import List

WORD_PATTERN = regex.compile(r"\p{L}+(?:[-‐-―]\p{L}+)*", regex.UNICODE)
ROMAN_NUMERAL = regex.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")
VALID_SINGLE_CHARS = {"a", "e", "o", "y", "i", "u"}


def count_words(text: str) -> int:
    if not text:
        return 0
    count = 0
    for match in WORD_PATTERN.finditer(text):
        token = match.group(0)
        if _is_valid_word(token):
            count += 1
    return count


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
