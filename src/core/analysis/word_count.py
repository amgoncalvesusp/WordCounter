"""Word-count analyzer (full PDF and analytical corpus)."""

from typing import Dict, List

from .base import ColumnSpec, DocumentContext
from ..word_counter import count_total, count_words


class WordCountAnalyzer:
    name = "word_count"

    def columns(self) -> List[ColumnSpec]:
        return [
            ColumnSpec("words_total", "Palavras (PDF Completo)", 18),
            ColumnSpec("words_analytical", "Palavras (Corpus Analítico)", 22),
        ]

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        total = count_total(ctx.pages_text)
        analytical = sum(
            count_words(ctx.pages_text[p - 1]) for p in ctx.analytical_page_numbers
        )
        return {"words_total": total, "words_analytical": analytical}
