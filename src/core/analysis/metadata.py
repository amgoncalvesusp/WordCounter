"""Document metadata analyzer (year, optional president, document type)."""

from typing import Dict, List

from .base import ColumnSpec, DocumentContext
from ..metadata_detector import detect_metadata


class MetadataAnalyzer:
    name = "metadata"

    def __init__(self, detect_president: bool = True):
        self.detect_president = detect_president

    def columns(self) -> List[ColumnSpec]:
        cols = [ColumnSpec("year", "Ano", 8)]
        if self.detect_president:
            cols.append(ColumnSpec("president", "Presidente", 28))
        cols.append(ColumnSpec("document", "Documento", 32))
        return cols

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        md = detect_metadata(
            ctx.pages_text, ctx.filename, detect_president=self.detect_president
        )
        # "president" key is always present so downstream consumers can use a
        # plain lookup; it is blank when detection is disabled.
        return {
            "year": md["year"],
            "president": md["president"],
            "document": md["document"],
        }
