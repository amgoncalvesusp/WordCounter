"""Detect document metadata from PDF content."""
import regex
from typing import Dict, Optional, List
from collections import Counter

PRESIDENTS = [
    ("Fernando Henrique Cardoso", 1995, 2002, ["Fernando Henrique Cardoso", "FHC"]),
    ("Luiz Inácio Lula da Silva", 2003, 2010, ["Luiz Inácio Lula", "Lula da Silva"]),
    ("Dilma Rousseff", 2011, 2016, ["Dilma Rousseff", "Dilma Vana Rousseff"]),
    ("Michel Temer", 2016, 2018, ["Michel Temer", "Michel Miguel Elias Temer"]),
    ("Jair Bolsonaro", 2019, 2022, ["Jair Bolsonaro", "Jair Messias Bolsonaro"]),
    ("Luiz Inácio Lula da Silva", 2023, 2026, ["Luiz Inácio Lula", "Lula da Silva"]),
]

YEAR_PATTERN = regex.compile(r"\b(199\d|20[0-3]\d)\b")
MENSAGEM_PATTERN = regex.compile(r"mensagem\s+(?:ao\s+)?congresso", regex.IGNORECASE)


def detect_metadata(pages_text: List[str], filename: str = "") -> Dict[str, str]:
    head_text = "\n".join(pages_text[:5])
    year = _detect_year(head_text, filename)
    president = _detect_president(head_text, year)
    document = _detect_document_type(head_text, filename)
    return {
        "year": year or "",
        "president": president or "",
        "document": document or "Mensagem ao Congresso Nacional",
    }


def _detect_year(text: str, filename: str = "") -> Optional[str]:
    matches = YEAR_PATTERN.findall(text)
    if matches:
        most_common = Counter(matches).most_common(1)
        if most_common:
            return most_common[0][0]
    fname_match = YEAR_PATTERN.search(filename)
    if fname_match:
        return fname_match.group(0)
    return None


def _detect_president(text: str, year: Optional[str]) -> Optional[str]:
    text_lower = text.lower()
    for canonical, _start, _end, variants in PRESIDENTS:
        for variant in variants:
            if variant.lower() in text_lower:
                if year:
                    try:
                        y = int(year)
                        if _start <= y <= _end:
                            return canonical
                    except ValueError:
                        pass
                else:
                    return canonical
    if year:
        try:
            y = int(year)
            for canonical, start, end, _ in PRESIDENTS:
                if start <= y <= end:
                    return canonical
        except ValueError:
            pass
    return None


def _detect_document_type(text: str, filename: str = "") -> Optional[str]:
    if MENSAGEM_PATTERN.search(text) or "mensagem" in filename.lower():
        return "Mensagem ao Congresso Nacional"
    return None
