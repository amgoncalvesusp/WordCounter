"""Unit tests for analytical-corpus page classification."""

import pytest

from src.core.corpus_filter import classify_all_pages, classify_page

pytestmark = pytest.mark.unit

CONTENT = " ".join(["palavra"] * 120)  # well above the editorial threshold


def test_blank_page_excluded():
    is_analytical, reason = classify_page("   ", 5, 20)
    assert is_analytical is False
    assert "branco" in reason


def test_ficha_catalografica_excluded():
    is_analytical, reason = classify_page(
        "Ficha Catalográfica\nCDD 320\nISBN 1234", 5, 20
    )
    assert is_analytical is False
    assert "ficha_catalografica" in reason


def test_normal_content_page_is_analytical():
    is_analytical, reason = classify_page(CONTENT, 5, 20)
    assert is_analytical is True
    assert reason == ""


def test_table_of_contents_excluded():
    toc = "Capítulo 1 ....... 10\nCapítulo 2 ....... 25\nCapítulo 3 ....... 40"
    is_analytical, reason = classify_page(toc, 6, 20)
    assert is_analytical is False


def test_classify_all_pages_shape():
    results = classify_all_pages(["   ", CONTENT])
    assert results[0]["page_number"] == 1
    assert results[0]["is_analytical"] is False
    assert results[1]["page_number"] == 2
    assert results[1]["is_analytical"] is True
    assert results[1]["word_count"] > 0
