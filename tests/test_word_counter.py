"""Unit tests for the word-counting engine."""

import pytest

from src.core.word_counter import count_total, count_words

pytestmark = pytest.mark.unit


def test_empty_string_counts_zero():
    assert count_words("") == 0


def test_counts_plain_words():
    assert count_words("O gato preto correu") == 4  # "O" -> valid single char


def test_invalid_single_chars_excluded():
    # "b" and "c" are not in the valid single-letter set.
    assert count_words("b c") == 0


def test_roman_numerals_excluded():
    assert count_words("Capítulo III") == 1  # "III" dropped


def test_lowercase_roman_like_word_kept():
    # Lowercase "ii" is not uppercase, so it is not treated as a numeral.
    assert count_words("mix") == 1


def test_hyphenated_word_counts_once():
    assert count_words("guarda-chuva") == 1


def test_count_total_sums_pages():
    assert count_total(["a b", "gato preto"]) == 3  # 1 + 2


def test_count_total_empty_list():
    assert count_total([]) == 0
