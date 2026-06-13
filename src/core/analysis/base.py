"""Core abstractions for the pluggable analysis pipeline.

An ``Analyzer`` consumes a :class:`DocumentContext` (text extracted once per
PDF) and returns a flat ``dict`` of result values keyed by column. Each analyzer
also declares the columns it contributes via :meth:`Analyzer.columns`, so the
exporter and GUI can build their schemas dynamically instead of hardcoding them.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Protocol, runtime_checkable


@dataclass(frozen=True)
class ColumnSpec:
    """Describes one output column contributed by an analyzer."""

    key: str
    label: str
    width: int = 14
    group: str = "base"  # styling group: "base", "term", "sentiment", ...


@dataclass
class DocumentContext:
    """Everything an analyzer needs about a single document.

    Built once per PDF after text extraction, then shared across all analyzers.
    """

    filename: str
    pages_text: List[str]
    analytical_page_numbers: List[int]
    total_pages: int
    stats: Dict[str, int] = field(default_factory=dict)


@runtime_checkable
class Analyzer(Protocol):
    """Contract every analysis plugin must satisfy."""

    name: str

    def columns(self) -> List[ColumnSpec]:
        """Ordered columns this analyzer contributes to the output schema."""
        ...

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        """Return a flat mapping of column key -> value for the document."""
        ...
