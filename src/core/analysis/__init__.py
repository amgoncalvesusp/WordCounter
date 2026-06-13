"""Pluggable document-analysis pipeline.

Public surface:
    - Analyzer, ColumnSpec, DocumentContext  : core abstractions
    - build_default_analyzers(...)            : standard analyzer set
    - build_column_specs(...)                 : full ordered output schema
"""

from typing import List, Tuple

from .base import Analyzer, ColumnSpec, DocumentContext
from .climate_policy import ClimatePolicyAnalyzer
from .doc_stats import DocStatsAnalyzer
from .keywords import KeywordAnalyzer
from .kwic import KwicAnalyzer
from .lexical_diversity import LexicalDiversityAnalyzer
from .metadata import MetadataAnalyzer
from .readability import ReadabilityAnalyzer
from .sentiment import SentimentAnalyzer
from .term_search import TermSearchAnalyzer
from .word_count import WordCountAnalyzer

__all__ = [
    "Analyzer",
    "ClimatePolicyAnalyzer",
    "ColumnSpec",
    "DocumentContext",
    "DocStatsAnalyzer",
    "KeywordAnalyzer",
    "KwicAnalyzer",
    "LexicalDiversityAnalyzer",
    "MetadataAnalyzer",
    "ReadabilityAnalyzer",
    "SentimentAnalyzer",
    "TermSearchAnalyzer",
    "WordCountAnalyzer",
    "build_default_analyzers",
    "build_column_specs",
]


def build_default_analyzers(
    search_terms: List[Tuple[str, bool]] = None,
    detect_president: bool = True,
    detect_sentiment: bool = True,
    detect_textmetrics: bool = True,
    detect_kwic: bool = True,
    detect_climate_policy: bool = True,
) -> List[Analyzer]:
    """Standard analyzer set, in output-column order."""
    analyzers: List[Analyzer] = [
        MetadataAnalyzer(detect_president=detect_president),
        DocStatsAnalyzer(),
        WordCountAnalyzer(),
    ]
    if detect_textmetrics:
        analyzers.append(ReadabilityAnalyzer())
        analyzers.append(LexicalDiversityAnalyzer())
        analyzers.append(KeywordAnalyzer())
    if detect_sentiment:
        analyzers.append(SentimentAnalyzer())
    if detect_climate_policy:
        analyzers.append(ClimatePolicyAnalyzer())
    analyzers.append(TermSearchAnalyzer(search_terms or []))
    if detect_kwic:
        # Detail-only (no columns); produces concordance lines for the terms.
        analyzers.append(KwicAnalyzer(search_terms or []))
    return analyzers


def build_column_specs(analyzers: List[Analyzer]) -> List[ColumnSpec]:
    """Full ordered column schema: id + filename, analyzer columns, then tail."""
    specs: List[ColumnSpec] = [
        ColumnSpec("doc_id", "Nº Doc.", 8),
        ColumnSpec("filename", "Nome do Arquivo", 35),
    ]
    for analyzer in analyzers:
        specs.extend(analyzer.columns())
    specs.append(ColumnSpec("confidence", "Grau de Confiança", 14))
    specs.append(ColumnSpec("observations", "Observações", 50))
    return specs
