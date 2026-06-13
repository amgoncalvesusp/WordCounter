"""Unit tests for the analyzer factory and column schema."""

import pytest

from src.core.analysis import (
    DocumentContext,
    build_column_specs,
    build_default_analyzers,
)

pytestmark = pytest.mark.unit


def test_default_set_includes_all_analyzers():
    names = [a.name for a in build_default_analyzers([])]
    assert names == [
        "metadata",
        "doc_stats",
        "word_count",
        "readability",
        "lexical_diversity",
        "keywords",
        "sentiment",
        "climate_policy",
        "term_search",
        "kwic",
    ]


def test_sentiment_can_be_disabled():
    names = [a.name for a in build_default_analyzers([], detect_sentiment=False)]
    assert "sentiment" not in names


def test_textmetrics_can_be_disabled():
    names = [a.name for a in build_default_analyzers([], detect_textmetrics=False)]
    for n in ("readability", "lexical_diversity", "keywords"):
        assert n not in names


def test_kwic_can_be_disabled():
    names = [a.name for a in build_default_analyzers([], detect_kwic=False)]
    assert "kwic" not in names


def test_climate_policy_can_be_disabled():
    names = [
        a.name for a in build_default_analyzers([], detect_climate_policy=False)
    ]
    assert "climate_policy" not in names


def test_column_specs_prefix_and_suffix():
    specs = build_column_specs(build_default_analyzers([], detect_sentiment=False))
    keys = [s.key for s in specs]
    assert keys[0] == "doc_id"
    assert keys[1] == "filename"
    assert keys[-2] == "confidence"
    assert keys[-1] == "observations"


def test_president_column_absent_when_disabled():
    specs = build_column_specs(
        build_default_analyzers([], detect_president=False, detect_sentiment=False)
    )
    assert "president" not in [s.key for s in specs]


def test_term_columns_generated_per_term():
    specs = build_column_specs(
        build_default_analyzers([("clima", False)], detect_sentiment=False)
    )
    keys = [s.key for s in specs]
    assert "_term_clima_total" in keys
    assert "_term_clima_analytical" in keys


def test_document_context_defaults():
    ctx = DocumentContext("a.pdf", ["x"], [1], 1)
    assert ctx.stats == {}
