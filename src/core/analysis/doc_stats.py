"""Intrinsic extraction statistics (pages, OCR usage)."""

from typing import Dict, List

from .base import ColumnSpec, DocumentContext


class DocStatsAnalyzer:
    name = "doc_stats"

    def columns(self) -> List[ColumnSpec]:
        return [
            ColumnSpec("total_pages", "Total de Páginas", 12),
            ColumnSpec("pages_with_text", "Páginas c/ Texto", 14),
            ColumnSpec("pages_problematic", "Páginas Problemáticas", 16),
            ColumnSpec("ocr_pages_count", "Páginas c/ OCR", 12),
        ]

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        stats = ctx.stats
        return {
            "total_pages": ctx.total_pages,
            "pages_with_text": stats.get("pages_with_text", 0),
            "pages_problematic": stats.get("pages_problematic", 0),
            "ocr_pages_count": stats.get("ocr_pages_count", 0),
        }
