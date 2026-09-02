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

import regex

from .base import ColumnSpec, DocumentContext
from ..term_search import normalize, term_token_patterns
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

        # Compile each term into its alternatives, one regex per word token,
        # so wildcards and "|" alternatives behave exactly as in the counts.
        term_seqs = [
            (
                term,
                [
                    [regex.compile(token) for token in alternative]
                    for alternative in term_token_patterns(term, exact)
                ],
            )
            for term, exact in self.terms
        ]

        lines: List[Dict[str, object]] = []
        for page in ctx.analytical_page_numbers:
            tokens = [
                m.group(0) for m in WORD_PATTERN.finditer(ctx.pages_text[page - 1])
            ]
            norm = [normalize(t) for t in tokens]
            for term, alternatives in term_seqs:
                for i in range(len(norm)):
                    for seq in alternatives:
                        n = len(seq)
                        if i + n > len(norm):
                            continue
                        if not all(
                            pattern.fullmatch(norm[i + j])
                            for j, pattern in enumerate(seq)
                        ):
                            continue
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
                        break  # one concordance line per position per term
        return {"kwic": lines}
