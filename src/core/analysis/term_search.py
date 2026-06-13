"""Term/phrase search analyzer (dynamic columns per search term)."""

from typing import Dict, List, Tuple

from .base import ColumnSpec, DocumentContext
from ..term_search import search_all_terms


class TermSearchAnalyzer:
    name = "term_search"

    def __init__(self, terms: List[Tuple[str, bool]] = None):
        self.terms = terms or []

    def _labels(self) -> List[str]:
        return [f'"{term}"' if exact else term for term, exact in self.terms]

    def columns(self) -> List[ColumnSpec]:
        cols: List[ColumnSpec] = []
        for label in self._labels():
            cols.append(
                ColumnSpec(f"_term_{label}_total", f"{label}\n(PDF)", 14, "term")
            )
            cols.append(
                ColumnSpec(
                    f"_term_{label}_analytical", f"{label}\n(Corpus)", 14, "term"
                )
            )
        return cols

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        results = search_all_terms(
            ctx.pages_text, self.terms, ctx.analytical_page_numbers
        )
        out: Dict[str, object] = {"term_results": results}
        for label, data in results.items():
            out[f"_term_{label}_total"] = data["total"]
            out[f"_term_{label}_analytical"] = data["analytical"]
        return out
