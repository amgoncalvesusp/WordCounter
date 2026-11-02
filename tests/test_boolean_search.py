"""Boolean queries preserve the existing term search rules."""

from dataclasses import FrozenInstanceError

import pytest

from src.core.boolean_search import compile_query


pytestmark = pytest.mark.unit


def test_boolean_precedence_and_parentheses():
    fields = {"ementa": "Carbono e agricultura"}
    assert compile_query("clima OR carbono AND agricultura").match(fields).matched
    assert not compile_query("(clima OR carbono) AND energia").match(fields).matched
    assert compile_query("carbono AND NOT energia").match(fields).matched
    assert not compile_query("NOT NOT energia").match(fields).matched


def test_and_combines_fields_but_phrase_does_not_cross_them():
    fields = {"ementa": "Mudanças", "indexacao": "climáticas"}
    assert compile_query("mudanç* AND climátic*").match(fields).matched
    assert not compile_query("mudanç* climátic*").match(fields).matched


def test_wildcard_alternatives_accents_and_word_boundaries():
    query = compile_query("mudanç* d* clima | mudanç* climátic*")
    assert query.match({"ementa": "MUDANÇAS CLIMÁTICAS"}).matched
    assert query.match({"ementa": "mudança do clima"}).matched
    assert not compile_query("clima").match({"ementa": "climatização"}).matched
    assert compile_query("clima or carbono").match({"ementa": "carbono"}).matched


def test_quoted_terms_keep_operators_and_wildcards_literal():
    assert compile_query('"clima AND energia"').match({"texto": "clima AND energia"}).matched
    assert compile_query("'clima | energia'").match({"texto": "clima | energia"}).matched
    assert not compile_query('"climátic*"').match({"texto": "climáticas"}).matched
    assert compile_query('"climátic*"').match({"texto": "climátic*"}).matched


def test_evidence_has_original_text_and_only_supporting_branches():
    fields = {"ementa": "Clima e ENERGIA renovável", "indexacao": "agricultura"}
    result = compile_query("(clima AND energia) OR (agricultura AND carvão)").match(fields)
    assert result.matched
    assert {item.term for item in result.evidence} == {"clima", "energia"}
    assert all(item.field == "ementa" for item in result.evidence)
    assert all("ENERGIA" in item.snippet for item in result.evidence)
    with pytest.raises(FrozenInstanceError):
        result.matched = False


def test_not_true_returns_no_positive_evidence_and_empty_text_is_not_a_hit():
    query = compile_query("NOT carbono")
    assert query.match({"ementa": "agricultura"}).matched
    assert query.match({"ementa": "agricultura"}).evidence == ()
    assert not query.match({"ementa": "  ", "indexacao": ""}).matched
    assert not query.match({}).matched


def test_negated_groups_preserve_positive_evidence_when_it_proves_the_result():
    fields = {"ementa": "Clima"}
    result = compile_query("NOT (NOT clima OR energia)").match(fields)
    assert result.matched
    assert tuple(item.term for item in result.evidence) == ("clima",)
    assert compile_query("NOT NOT clima").match(fields).evidence == result.evidence
    assert compile_query("NOT clima").match(fields).evidence == ()


def test_evidence_preserves_decomposed_accents():
    text = "A política de mudanc\u0327as climáticas será aplicada."
    result = compile_query("mudanç* climátic*").match({"ementa": text})
    assert result.matched
    assert "mudanc\u0327as climáticas" in result.evidence[0].snippet


@pytest.mark.parametrize("expression", [
    "", "   ", "*", "***", "AND clima", "clima AND", "clima OR OR energia",
    "clima NOT energia", "(clima", "clima)", "()", '"clima', "'clima",
    '""', '"clima" "energia"', "clima |", "| clima",
])
def test_invalid_queries_fail_clearly(expression):
    with pytest.raises(ValueError):
        compile_query(expression)


def test_limits_reject_excessively_long_or_deep_queries():
    for expression in ("x" * 10000, "(" * 80 + "clima" + ")" * 80,
                       " OR ".join("clima" for _ in range(300))):
        with pytest.raises(ValueError):
            compile_query(expression)


def test_compiled_query_reusable_and_does_not_change_input():
    query = compile_query("climátic* AND NOT escola")
    fields = {"ementa": "Políticas climáticas"}
    assert query.expression == "climátic* AND NOT escola"
    assert query.match(fields).matched
    assert not query.match({"ementa": "Escola climática"}).matched
    assert query.match(fields).matched
    assert fields == {"ementa": "Políticas climáticas"}


def test_non_text_input_is_rejected_at_boundary():
    with pytest.raises(ValueError):
        compile_query(None)
    with pytest.raises(ValueError):
        compile_query("clima").match({"ementa": 42})
