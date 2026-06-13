"""Unit tests for the sentiment analyzer (LeIA / VADER-PT)."""

import pytest

from src.core.analysis.base import DocumentContext
from src.core.analysis.sentiment import (
    NEGATIVE,
    NEUTRAL,
    POSITIVE,
    SentimentAnalyzer,
    classify,
    segment_sentences,
)

pytestmark = pytest.mark.unit


def test_segment_basic_sentences():
    assert segment_sentences("A economia cresceu! Foi bom? Sim.") == [
        "A economia cresceu!",
        "Foi bom?",
        "Sim.",
    ]


def test_segment_guards_abbreviation():
    # "Sr." must not split the sentence.
    assert segment_sentences("O Sr. Lula falou hoje.") == ["O Sr. Lula falou hoje."]


def test_segment_guards_enumeration():
    assert segment_sentences("Vejamos o item 1. Agora o resto.") == [
        "Vejamos o item 1. Agora o resto."
    ]


def test_segment_empty():
    assert segment_sentences("   ") == []


def test_classify_thresholds():
    assert classify(0.5) == POSITIVE
    assert classify(-0.5) == NEGATIVE
    assert classify(0.0) == NEUTRAL


def test_analyzer_scores_polarity():
    # Engine integration: clearly positive vs clearly negative text.
    engine = SentimentAnalyzer()._analyzer()
    assert engine.polarity_scores("O resultado foi excelente e otimo")["compound"] > 0
    assert engine.polarity_scores("A crise foi terrivel e pessima")["compound"] < 0


def test_analyzer_output_keys_and_aggregates():
    ctx = DocumentContext(
        "doc.pdf",
        ["O pais avancou e conquistou grandes vitorias. A crise foi terrivel."],
        [1],
        1,
    )
    out = SentimentAnalyzer().run(ctx)
    for key in (
        "sent_classe",
        "sent_compound_medio",
        "sent_pct_positivo",
        "sent_pct_negativo",
        "sent_pct_neutro",
        "sent_n_sentencas",
        "sentiment_sentences",
    ):
        assert key in out
    assert out["sent_n_sentencas"] == 2
    assert len(out["sentiment_sentences"]) == 2
    assert out["sentiment_sentences"][0]["page"] == 1


def test_analyzer_empty_corpus():
    ctx = DocumentContext("doc.pdf", ["capa"], [], 1)
    out = SentimentAnalyzer().run(ctx)
    assert out["sent_n_sentencas"] == 0
    assert out["sent_classe"] == NEUTRAL
    assert out["sentiment_sentences"] == []
