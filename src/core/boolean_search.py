"""Compiled, auditable boolean searches over selected text fields."""

from dataclasses import dataclass
from typing import Mapping

import regex

from .term_search import normalize, term_token_patterns


MAX_QUERY_CHARS = 8192
MAX_TOKENS = 256
MAX_DEPTH = 32
_LEXER = regex.compile(
    r'''\s+|"[^"]*"|'[^']*'|\b(?:AND|OR|NOT)\b|[()|]|[^\s()|"']+''',
    regex.IGNORECASE,
)


@dataclass(frozen=True)
class SearchEvidence:
    field: str
    term: str
    snippet: str


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    evidence: tuple[SearchEvidence, ...] = ()


def _tokens(expression):
    result = []
    end = 0
    for match in _LEXER.finditer(expression):
        if match.start() != end:
            raise ValueError("Aspas não fechadas na expressão de busca.")
        end = match.end()
        value = match.group()
        if value.isspace():
            continue
        operator = "OR" if value == "|" else value.upper()
        if operator in ("AND", "OR", "NOT", "(", ")"):
            result.append((operator, value))
        elif value[0] in ('"', "'"):
            result.append(("EXACT", value))
        elif result and result[-1][0] == "TERM":
            result[-1] = ("TERM", result[-1][1] + " " + value)
        else:
            result.append(("TERM", value))
        if len(result) > MAX_TOKENS:
            raise ValueError("Expressão longa demais: limite de 256 elementos.")
    if end != len(expression):
        raise ValueError("Aspas não fechadas na expressão de busca.")
    return result


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0
        self.terms = []

    def _accept(self, operator):
        if self.position < len(self.tokens) and self.tokens[self.position][0] == operator:
            self.position += 1
            return True
        return False

    def expression(self, depth=0):
        node = self._and(depth)
        while self._accept("OR"):
            node = ("OR", node, self._and(depth))
        return node

    def _and(self, depth):
        node = self._unary(depth)
        while self._accept("AND"):
            node = ("AND", node, self._unary(depth))
        return node

    def _unary(self, depth):
        if depth > MAX_DEPTH:
            raise ValueError("Expressão aninhada demais: limite de 32 níveis.")
        if self._accept("NOT"):
            return ("NOT", self._unary(depth + 1))
        if self._accept("("):
            node = self.expression(depth + 1)
            if not self._accept(")"):
                raise ValueError("Falta fechar parêntese na expressão de busca.")
            return node
        if self.position >= len(self.tokens):
            raise ValueError("Falta um termo na expressão de busca.")
        kind, label = self.tokens[self.position]
        if kind not in ("TERM", "EXACT"):
            raise ValueError(f"Esperado um termo; encontrado {label!r}.")
        self.position += 1
        text = label[1:-1].strip() if kind == "EXACT" else label
        alternatives = term_token_patterns(text, exact=kind == "EXACT")
        if not alternatives or not any(c.isalnum() for c in text):
            raise ValueError("Cada termo deve conter letras ou números.")
        if text.count("*") > 16:
            raise ValueError("Termo com curingas demais: limite de 16.")
        body = "|".join(r"\s+".join(parts) for parts in alternatives)
        pattern = regex.compile(r"(?<!\w)(?:" + body + r")(?!\w)")
        index = len(self.terms)
        self.terms.append((label, pattern))
        return ("TERM", index)


def _snippet(original, normalized, start, end):
    if len(original) != len(normalized):
        positions = [i for i, character in enumerate(original) for _ in normalize(character)]
        start, end = positions[start], positions[end - 1] + 1
    return " ".join(original[max(0, start - 80):end + 80].split())


def _evaluate(node, matches):
    operator = node[0]
    if operator == "TERM":
        return matches[node[1]]
    left = _evaluate(node[1], matches)
    if operator == "NOT":
        return MatchResult(not left.matched, left.evidence)
    right = _evaluate(node[2], matches)
    matched = left.matched and right.matched if operator == "AND" else left.matched or right.matched
    supporting = tuple(
        item for branch in (left, right)
        if branch.matched == matched for item in branch.evidence
    )
    return MatchResult(matched, supporting)


@dataclass(frozen=True)
class CompiledQuery:
    expression: str
    _tree: tuple
    _terms: tuple

    def match(self, fields: Mapping[str, str]) -> MatchResult:
        if not isinstance(fields, Mapping):
            raise ValueError("Forneça os campos de texto em um mapeamento.")
        normalized = []
        for field, text in fields.items():
            if not isinstance(field, str) or not isinstance(text, str):
                raise ValueError("Nomes de campos e conteúdos devem ser textos.")
            if text.strip():
                normalized.append((field, text, normalize(text)))
        if not normalized:
            return MatchResult(False)
        matches = []
        for label, pattern in self._terms:
            evidence = []
            for field, original, text in normalized:
                try:
                    found = pattern.search(text, timeout=0.2)
                except TimeoutError as error:
                    raise ValueError("Busca excedeu o tempo limite; simplifique os curingas.") from error
                if found:
                    evidence.append(SearchEvidence(field, label, _snippet(original, text, *found.span())))
            matches.append(MatchResult(bool(evidence), tuple(evidence)))
        result = _evaluate(self._tree, matches)
        evidence = tuple(dict.fromkeys(result.evidence)) if result.matched else ()
        return MatchResult(result.matched, evidence)


def compile_query(expression: str) -> CompiledQuery:
    """Parse NOT > AND > OR without evaluating user input as Python code."""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Informe uma expressão de busca.")
    expression = expression.strip()
    if len(expression) > MAX_QUERY_CHARS:
        raise ValueError("Expressão longa demais: limite de 8192 caracteres.")
    parser = _Parser(_tokens(expression))
    tree = parser.expression()
    if parser.position != len(parser.tokens):
        raise ValueError("Expressão inválida: confira operadores, aspas e parênteses.")
    return CompiledQuery(expression, tree, tuple(parser.terms))
