"""Lexical diversity analyzer.

Reports vocabulary richness over the analytical corpus:

- TTR (Type-Token Ratio): types / tokens — the classic measure (Templin, 1957).
  Sensitive to text length, so it is complemented by:
- Guiraud's index (R): types / sqrt(tokens) — more stable across lengths
  (Guiraud, 1954).

Token matching reuses the project's word tokenizer; types are compared
case-insensitively.
"""

import math
from typing import Dict, List

from .base import ColumnSpec, DocumentContext
from ..word_counter import tokenize


class LexicalDiversityAnalyzer:
    name = "lexical_diversity"

    def columns(self) -> List[ColumnSpec]:
        return [
            ColumnSpec("lex_ttr", "Diversidade (TTR)", 14, "text"),
            ColumnSpec("lex_guiraud", "Índice de Guiraud", 14, "text"),
            ColumnSpec("lex_vocabulario", "Vocabulário (tipos)", 14, "text"),
        ]

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        text = "\n".join(ctx.pages_text[p - 1] for p in ctx.analytical_page_numbers)
        tokens = [t.lower() for t in tokenize(text)]
        n_tokens = len(tokens)
        if n_tokens == 0:
            return {"lex_ttr": 0.0, "lex_guiraud": 0.0, "lex_vocabulario": 0}

        types = len(set(tokens))
        return {
            "lex_ttr": round(types / n_tokens, 4),
            "lex_guiraud": round(types / math.sqrt(n_tokens), 2),
            "lex_vocabulario": types,
        }
