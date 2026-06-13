"""Unit tests for the text-metric analyzers (readability, diversity, keywords)."""

import pytest

from src.core.analysis.base import DocumentContext
from src.core.analysis.keywords import STOPWORDS, KeywordAnalyzer
from src.core.analysis.lexical_diversity import LexicalDiversityAnalyzer
from src.core.analysis.readability import (
    ReadabilityAnalyzer,
    classify_ease,
    count_syllables,
)

pytestmark = pytest.mark.unit


# --- readability ---------------------------------------------------------


def test_count_syllables_vowel_groups():
    assert count_syllables("casa") == 2
    assert count_syllables("pais") == 1  # "ai" is one vowel group
    assert count_syllables("bcdf") == 1  # no vowels -> minimum 1


def test_classify_ease_bands():
    assert classify_ease(80) == "Muito fácil"
    assert classify_ease(60) == "Fácil"
    assert classify_ease(30) == "Difícil"
    assert classify_ease(10) == "Muito difícil"


def test_readability_keys_and_empty_corpus():
    out = ReadabilityAnalyzer().run(DocumentContext("d.pdf", ["capa"], [], 1))
    assert out["leg_classe"] == "—"
    assert out["leg_indice"] == 0.0

    ctx = DocumentContext(
        "d.pdf", ["O pais cresceu muito. A economia avancou."], [1], 1
    )
    out = ReadabilityAnalyzer().run(ctx)
    assert "leg_indice" in out
    assert out["leg_palavras_frase"] > 0


# --- lexical diversity ---------------------------------------------------


def test_lexical_diversity_basic():
    # 4 tokens, 2 types -> TTR 0.5
    ctx = DocumentContext("d.pdf", ["gato gato cao cao"], [1], 1)
    out = LexicalDiversityAnalyzer().run(ctx)
    assert out["lex_vocabulario"] == 2
    assert out["lex_ttr"] == 0.5
    assert out["lex_guiraud"] == pytest.approx(1.0, abs=0.01)


def test_lexical_diversity_empty():
    out = LexicalDiversityAnalyzer().run(DocumentContext("d.pdf", [""], [], 1))
    assert out["lex_ttr"] == 0.0
    assert out["lex_vocabulario"] == 0


# --- keywords ------------------------------------------------------------


def test_stopwords_loaded():
    assert "de" in STOPWORDS
    assert "que" in STOPWORDS
    assert len(STOPWORDS) > 50


def test_keyword_ranking_skips_stopwords():
    ctx = DocumentContext(
        "d.pdf",
        ["O desenvolvimento e o desenvolvimento do territorio com de da que"],
        [1],
        1,
    )
    out = KeywordAnalyzer().run(ctx)
    freq = dict(out["keyword_freq"])
    assert freq.get("desenvolvimento") == 2
    assert "que" not in freq  # stopword
    assert "de" not in freq
    assert out["kw_top"].startswith("desenvolvimento (2)")


def test_keyword_empty_corpus():
    out = KeywordAnalyzer().run(DocumentContext("d.pdf", ["x"], [], 1))
    assert out["keyword_freq"] == []
    assert out["kw_top"] == ""
