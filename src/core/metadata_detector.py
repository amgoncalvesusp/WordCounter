"""Detect document metadata from PDF content.

The list of heads of state is loaded from ``data/presidents.json`` so the tool
can be adapted to other countries/corpora without code changes. President
detection is optional (``detect_president``); year and document type are always
attempted.
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import regex

# Digit lookarounds (not \b) so years glued to underscores/letters in filenames
# (e.g. "mensagem_2015.pdf") are still detected, while runs of digits are not.
YEAR_PATTERN = regex.compile(r"(?<!\d)(199\d|20[0-3]\d)(?!\d)")
MENSAGEM_PATTERN = regex.compile(r"mensagem\s+(?:ao\s+)?congresso", regex.IGNORECASE)

# (canonical, start_year, end_year, variants)
President = Tuple[str, int, int, List[str]]


def _data_path() -> Path:
    """Resolve the presidents config path in both dev and frozen (PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "src" / "core" / "data"
    else:
        base = Path(__file__).resolve().parent / "data"
    return base / "presidents.json"


def _load_presidents() -> List[President]:
    """Load heads of state from JSON. Returns an empty list if unavailable."""
    try:
        with open(_data_path(), encoding="utf-8") as f:
            raw = json.load(f)
        return [
            (p["canonical"], int(p["start"]), int(p["end"]), list(p["variants"]))
            for p in raw.get("presidents", [])
        ]
    except (OSError, ValueError, KeyError):
        # Missing/corrupt config must not break the rest of the analysis.
        return []


PRESIDENTS: List[President] = _load_presidents()


def detect_metadata(
    pages_text: List[str], filename: str = "", detect_president: bool = True
) -> Dict[str, str]:
    head_text = "\n".join(pages_text[:5])
    year = _detect_year(head_text, filename)
    president = _detect_president(head_text, year) if detect_president else None
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
