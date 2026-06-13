"""Keyword-frequency analyzer.

Frequency of content words is the backbone of Bardin's content analysis and a
practical entry point for identifying recurring meaning units (núcleos de
significação). Stopwords are removed using an editable PT-BR list
(``data/stopwords_pt.txt``); the remaining words are ranked by frequency over
the analytical corpus.

Output:
- ``kw_top``: the top keywords as a compact "palavra (n); ..." string.
- ``keyword_freq``: the ranked list (word, count), exported to a detail sheet.
"""

import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from .base import ColumnSpec, DocumentContext
from ..term_search import normalize
from ..word_counter import tokenize

TOP_N_CELL = 10
TOP_N_SHEET = 30
MIN_LENGTH = 3

_FALLBACK_STOPWORDS = {
    "a",
    "o",
    "e",
    "de",
    "da",
    "do",
    "que",
    "em",
    "para",
    "com",
    "os",
    "as",
    "um",
    "uma",
    "no",
    "na",
    "se",
    "por",
    "dos",
    "das",
    "ao",
    "nao",
    "mais",
}


def _data_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "src" / "core" / "data"
    else:
        base = Path(__file__).resolve().parent.parent / "data"
    return base / "stopwords_pt.txt"


def _load_stopwords() -> set:
    """Load the PT-BR stopword list (accent-stripped). Fallback if unavailable."""
    try:
        with open(_data_path(), encoding="utf-8") as f:
            words = set()
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    words.add(normalize(line))
            return words or set(_FALLBACK_STOPWORDS)
    except OSError:
        return set(_FALLBACK_STOPWORDS)


STOPWORDS = _load_stopwords()


class KeywordAnalyzer:
    name = "keywords"

    def columns(self) -> List[ColumnSpec]:
        return [ColumnSpec("kw_top", "Palavras-chave (frequência)", 60, "text")]

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        text = "\n".join(ctx.pages_text[p - 1] for p in ctx.analytical_page_numbers)
        counter: Counter = Counter()
        for token in tokenize(text):
            display = token.lower()
            stripped = normalize(token)
            if len(stripped) < MIN_LENGTH or stripped in STOPWORDS:
                continue
            counter[display] += 1

        ranked: List[Tuple[str, int]] = counter.most_common(TOP_N_SHEET)
        cell = "; ".join(f"{w} ({c})" for w, c in ranked[:TOP_N_CELL])
        return {"kw_top": cell, "keyword_freq": ranked}
