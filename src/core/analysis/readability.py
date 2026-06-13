"""Readability analyzer for Brazilian Portuguese.

Uses the Flesch Reading Ease score adapted to Brazilian Portuguese:

    ILF = 248.835 − 1.015 × (palavras / frases) − 84.6 × (sílabas / palavras)

    Martins, T. B. F.; Ghiraldelo, C. M.; Nunes, M. G. V.; Oliveira Jr., O. N.
    (1996). Readability formulas applied to textbooks in Brazilian Portuguese.
    Notas do ICMC-USP, n. 28.

Syllable counting uses a vowel-group heuristic (each maximal run of vowels
counts as one syllable). This is an approximation — exact PT-BR syllabification
would require a hyphenation dictionary — and is reported as such.
"""

from typing import Dict, List

import regex

from .base import ColumnSpec, DocumentContext
from .sentiment import segment_sentences
from ..word_counter import tokenize

_VOWEL_GROUP = regex.compile(r"[aeiouáàâãéêíóôõúüy]+", regex.IGNORECASE)


def count_syllables(word: str) -> int:
    """Approximate syllable count via vowel groups (minimum 1)."""
    groups = _VOWEL_GROUP.findall(word.lower())
    return max(len(groups), 1)


def classify_ease(score: float) -> str:
    if score >= 75:
        return "Muito fácil"
    if score >= 50:
        return "Fácil"
    if score >= 25:
        return "Difícil"
    return "Muito difícil"


class ReadabilityAnalyzer:
    name = "readability"

    def columns(self) -> List[ColumnSpec]:
        return [
            ColumnSpec("leg_indice", "Legibilidade (Flesch-PT)", 18, "text"),
            ColumnSpec("leg_classe", "Legibilidade (classe)", 16, "text"),
            ColumnSpec("leg_palavras_frase", "Palavras / frase", 14, "text"),
            ColumnSpec("leg_silabas_palavra", "Sílabas / palavra", 14, "text"),
        ]

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        text = "\n".join(ctx.pages_text[p - 1] for p in ctx.analytical_page_numbers)
        words = tokenize(text)
        sentences = segment_sentences(text)
        n_words = len(words)
        n_sentences = len(sentences)

        if n_words == 0 or n_sentences == 0:
            return {
                "leg_indice": 0.0,
                "leg_classe": "—",
                "leg_palavras_frase": 0.0,
                "leg_silabas_palavra": 0.0,
            }

        syllables = sum(count_syllables(w) for w in words)
        words_per_sentence = n_words / n_sentences
        syllables_per_word = syllables / n_words
        ilf = 248.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
        ilf = round(ilf, 1)
        return {
            "leg_indice": ilf,
            "leg_classe": classify_ease(ilf),
            "leg_palavras_frase": round(words_per_sentence, 1),
            "leg_silabas_palavra": round(syllables_per_word, 2),
        }
