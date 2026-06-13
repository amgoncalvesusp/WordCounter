"""Unit tests for the term/phrase search engine."""

import pytest

from src.core.term_search import (
    count_term,
    normalize,
    parse_terms,
    search_all_terms,
)

pytestmark = pytest.mark.unit


def test_parse_terms_skips_comments_and_blanks():
    raw = "clima\n# comentario\n\n  \ndesmatamento"
    assert parse_terms(raw) == [("clima", False), ("desmatamento", False)]


def test_parse_terms_quotes_mark_exact():
    assert parse_terms('"efeito estufa"') == [("efeito estufa", True)]
    assert parse_terms("'mudança do clima'") == [("mudança do clima", True)]


def test_normalize_strips_accents_and_lowercases():
    assert normalize("Mudança") == "mudanca"
    assert normalize("Mudança", strip_accents=False) == "mudança"


def test_count_term_is_accent_insensitive():
    assert count_term("Mudança e mudanca do clima", "mudanca") == 2


def test_count_term_respects_word_boundaries():
    # "clima" should not match inside "climatico".
    assert count_term("clima climatico clima", "clima") == 2


def test_count_term_phrase():
    assert count_term("o efeito estufa e o efeito estufa", "efeito estufa") == 2


def test_count_term_empty_inputs():
    assert count_term("", "clima") == 0
    assert count_term("clima", "") == 0


def test_search_all_terms_total_vs_analytical():
    pages = ["clima clima", "clima", "clima"]
    terms = [("clima", False)]
    # Only pages 1 and 2 are analytical.
    results = search_all_terms(pages, terms, analytical_pages=[1, 2])
    assert results["clima"]["total"] == 4
    assert results["clima"]["analytical"] == 3


def test_search_all_terms_exact_label_quoted():
    results = search_all_terms(["efeito estufa"], [("efeito estufa", True)], None)
    assert '"efeito estufa"' in results
