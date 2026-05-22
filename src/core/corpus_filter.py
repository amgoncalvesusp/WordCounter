"""Identify pages to EXCLUDE from analytical corpus."""
import regex
from typing import List, Dict, Tuple
from .word_counter import count_words

EXCLUSION_KEYWORDS = {
    "ficha_catalografica": [
        r"ficha\s+catalogr[áa]fica",
        r"cataloga[çc][ãa]o\s+na\s+(?:fonte|publica[çc][ãa]o)",
        r"\bCDD\b", r"\bCDU\b", r"\bISBN\b",
        r"biblioteca\s+da\s+presid[êe]ncia",
    ],
    "sumario": [
        r"^\s*SUM[ÁA]RIO\s*$",
        r"^\s*[ÍI]NDICE\s*$",
        r"^\s*CONTE[ÚU]DO\s*$",
    ],
    "expediente": [
        r"^\s*EXPEDIENTE\s*$",
    ],
    "folha_rosto": [
        r"mensagem\s+ao\s+congresso\s+nacional",
    ],
    "ministros_list": [
        r"ministros?\s+de\s+estado",
        r"composi[çc][ãa]o\s+do\s+minist[ée]rio",
    ],
}

EDITORIAL_WORD_THRESHOLD = 80
TOC_PATTERN = regex.compile(r"\.{4,}\s*\d+", regex.MULTILINE)


def classify_page(page_text: str, page_index: int, total_pages: int) -> Tuple[bool, str]:
    if not page_text or not page_text.strip():
        return (False, "página em branco")

    word_count = count_words(page_text)
    text_lower = page_text.lower()

    for category, patterns in EXCLUSION_KEYWORDS.items():
        for pattern in patterns:
            if regex.search(pattern, text_lower, regex.IGNORECASE | regex.MULTILINE):
                if word_count < EDITORIAL_WORD_THRESHOLD * 3:
                    return (False, f"detectado: {category}")

    toc_matches = len(TOC_PATTERN.findall(page_text))
    if toc_matches >= 3 and word_count < 500:
        return (False, "sumário (padrão de linhas pontilhadas)")

    if page_index < max(3, int(total_pages * 0.05)) and word_count < EDITORIAL_WORD_THRESHOLD:
        return (False, "página inicial com texto reduzido")

    if page_index < 2 and word_count < 50:
        return (False, "provável capa")

    return (True, "")


def classify_all_pages(pages_text: List[str]) -> List[Dict]:
    total = len(pages_text)
    results = []
    for i, text in enumerate(pages_text):
        is_analytical, reason = classify_page(text, i, total)
        word_count = count_words(text)
        results.append({
            "page_number": i + 1,
            "is_analytical": is_analytical,
            "exclusion_reason": reason,
            "word_count": word_count,
        })
    return results
