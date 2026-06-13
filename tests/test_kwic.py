"""Unit tests for the KWIC (keyword-in-context) analyzer."""

import pytest

from src.core.analysis.base import DocumentContext
from src.core.analysis.kwic import KwicAnalyzer

pytestmark = pytest.mark.unit


def test_no_columns_contributed():
    assert KwicAnalyzer([("clima", False)]).columns() == []


def test_empty_terms_yield_no_lines():
    ctx = DocumentContext("d.pdf", ["o clima mudou"], [1], 1)
    assert KwicAnalyzer([]).run(ctx)["kwic"] == []


def test_finds_each_occurrence_with_context():
    ctx = DocumentContext("d.pdf", ["o clima mudou e o clima aqueceu"], [1], 1)
    lines = KwicAnalyzer([("clima", False)], window=2).run(ctx)["kwic"]
    assert len(lines) == 2
    first = lines[0]
    assert first["keyword"] == "clima"
    assert first["left"] == "o"
    assert first["right"] == "mudou e"
    assert first["page"] == 1
    assert first["term"] == "clima"


def test_accent_insensitive_keeps_original_spelling():
    ctx = DocumentContext("d.pdf", ["a mudança do clima"], [1], 1)
    lines = KwicAnalyzer([("mudanca", False)]).run(ctx)["kwic"]
    assert len(lines) == 1
    assert lines[0]["keyword"] == "mudança"  # original accent preserved


def test_multiword_phrase_matches_as_unit():
    ctx = DocumentContext("d.pdf", ["o efeito estufa aumentou"], [1], 1)
    lines = KwicAnalyzer([("efeito estufa", True)]).run(ctx)["kwic"]
    assert len(lines) == 1
    assert lines[0]["keyword"] == "efeito estufa"
    assert lines[0]["right"] == "aumentou"


def test_only_searches_analytical_pages():
    ctx = DocumentContext("d.pdf", ["clima na capa", "clima no corpo"], [2], 2)
    lines = KwicAnalyzer([("clima", False)]).run(ctx)["kwic"]
    assert len(lines) == 1
    assert lines[0]["page"] == 2
