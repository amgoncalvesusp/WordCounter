"""KWIC — Keyword-In-Context (concordância).

For each search term, records the surrounding context of every occurrence in the
analytical corpus. KWIC is a *qualitative* output: it produces no aggregate
column, only concordance lines (left context / keyword / right context) written
to a dedicated XLSX sheet. This is the *unidade de contexto* of Bardin's content
analysis — it lets the researcher read each occurrence in situ instead of only
counting it.

Matching mirrors the term-search engine: accent-insensitive, at the word-token
level (so multi-word terms match consecutive tokens). Context preserves the
original spelling of surrounding words for readability.
"""

from typing import Dict, List, Tuple

from .base import ColumnSpec, DocumentContext
from ..term_search import normalize
from ..word_counter import WORD_PATTERN

CONTEXT_WINDOW = 8  # words of context on each side
MAX_LINES_PER_DOC = 1000  # safety cap to keep the sheet bounded


class KwicAnalyzer:
    name = "kwic"

    def __init__(
        self, terms: List[Tuple[str, bool]] = None, window: int = CONTEXT_WINDOW
    ):
        self.terms = terms or []
        self.window = window

    def columns(self) -> List[ColumnSpec]:
        # Detail-only analyzer: contributes no main-table column.
        return []

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        if not self.terms:
            return {"kwic": []}

        # Pre-normalize each term into its token sequence.
        term_seqs = [
            (term, [normalize(w) for w in term.split() if normalize(w)])
            for term, _exact in self.terms
        ]

        lines: List[Dict[str, object]] = []
        for page in ctx.analytical_page_numbers:
            tokens = [
                m.group(0) for m in WORD_PATTERN.finditer(ctx.pages_text[page - 1])
            ]
            norm = [normalize(t) for t in tokens]
            for term, seq in term_seqs:
                n = len(seq)
                if n == 0:
                    continue
                for i in range(len(norm) - n + 1):
                    if norm[i : i + n] == seq:
                        left = " ".join(tokens[max(0, i - self.window) : i])
                        keyword = " ".join(tokens[i : i + n])
                        right = " ".join(tokens[i + n : i + n + self.window])
                        lines.append(
                            {
                                "page": page,
                                "term": term,
                                "left": left,
                                "keyword": keyword,
                                "right": right,
                            }
                        )
                        if len(lines) >= MAX_LINES_PER_DOC:
                            return {"kwic": lines}
        return {"kwic": lines}
