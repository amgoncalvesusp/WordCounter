"""Sentiment analyzer for Brazilian Portuguese.

Methodology
-----------
Rule-based valence scoring with the VADER model (Valence Aware Dictionary and
sEntiment Reasoner), adapted to Brazilian Portuguese by LeIA (Léxico para
Inferência Adaptada). VADER combines a human-validated sentiment lexicon with
grammatical/syntactic heuristics — negation handling, intensity boosters,
ALL-CAPS emphasis and punctuation — producing a normalized ``compound`` score in
[-1, +1].

    Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model
    for Sentiment Analysis of Social Media Text. ICWSM-14.
    LeIA: Almeida, R. J. de A. https://github.com/rafjaa/LeIA

Why this serves qualitative content analysis
---------------------------------------------
Scoring is performed at the **sentence** level, the natural unit of registry for
Bardin's *Análise de Conteúdo* and the affective pre-indicators of Aguiar &
Ozella's *Núcleos de Significação*. Every scored sentence is retained with its
page and valence class, so the researcher can trace each aggregate back to the
exact textual unit (full transparency / auditability) and cluster affect-laden
sentences into indicators and meaning nuclei.

    Bardin, L. (2011). Análise de Conteúdo. São Paulo: Edições 70.
    Aguiar, W. M. J. & Ozella, S. (2006/2013). Núcleos de significação como
    instrumento para a apreensão da constituição dos sentidos.
"""

import regex
from typing import Dict, List

from .base import ColumnSpec, DocumentContext

# Standard VADER classification thresholds on the normalized compound score
# (Hutto & Gilbert, 2014).
POS_THRESHOLD = 0.05
NEG_THRESHOLD = -0.05

POSITIVE = "Positivo"
NEGATIVE = "Negativo"
NEUTRAL = "Neutro"

# Sentence segmentation: split on terminal punctuation, but protect common
# Brazilian Portuguese abbreviations and enumerations so they do not create
# false boundaries.
_ABBREVIATIONS = {
    "sr",
    "sra",
    "srs",
    "sras",
    "dr",
    "dra",
    "prof",
    "profa",
    "exmo",
    "exma",
    "ex",
    "exa",
    "art",
    "arts",
    "inc",
    "par",
    "cap",
    "fl",
    "fls",
    "pag",
    "pags",
    "p",
    "pp",
    "n",
    "no",
    "nos",
    "cia",
    "ltda",
    "av",
    "etc",
    "v",
    "vs",
    "sto",
    "sta",
    "pe",
    "me",
    "obs",
    "ref",
    "seg",
    "min",
}
_SENTENCE_END = regex.compile(r"([.!?…]+)\s+", regex.UNICODE)
_TRAILING_TOKEN = regex.compile(r"(\p{L}+|\d+)[.!?…]+$", regex.UNICODE)


def segment_sentences(text: str) -> List[str]:
    """Split text into sentences, guarding abbreviations and enumerations."""
    if not text or not text.strip():
        return []

    flat = regex.sub(r"\s+", " ", text).strip()
    sentences: List[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(flat):
        candidate = flat[start : match.end()].strip()
        if _is_false_boundary(candidate):
            continue
        if candidate:
            sentences.append(candidate)
        start = match.end()

    tail = flat[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _is_false_boundary(candidate: str) -> bool:
    """True when the period closing ``candidate`` is an abbreviation/enumeration."""
    m = _TRAILING_TOKEN.search(candidate)
    if not m:
        return False
    token = m.group(1).lower()
    if token in _ABBREVIATIONS:
        return True
    # Single letter ("A.") or a bare number ("1.") — enumeration / initial.
    if len(token) == 1 or token.isdigit():
        return True
    return False


def classify(compound: float) -> str:
    if compound >= POS_THRESHOLD:
        return POSITIVE
    if compound <= NEG_THRESHOLD:
        return NEGATIVE
    return NEUTRAL


class SentimentAnalyzer:
    name = "sentiment"

    def __init__(self):
        # Lazily instantiated: loading the lexicon (~430 KB) is deferred until
        # the first document is actually processed.
        self._engine = None

    def _analyzer(self):
        if self._engine is None:
            from .vendor.leia import SentimentIntensityAnalyzer

            self._engine = SentimentIntensityAnalyzer()
        return self._engine

    def columns(self) -> List[ColumnSpec]:
        return [
            ColumnSpec("sent_classe", "Sentimento (classe)", 16, "sentiment"),
            ColumnSpec(
                "sent_compound_medio", "Sentimento (composto médio)", 18, "sentiment"
            ),
            ColumnSpec("sent_pct_positivo", "% Sentenças Positivas", 16, "sentiment"),
            ColumnSpec("sent_pct_negativo", "% Sentenças Negativas", 16, "sentiment"),
            ColumnSpec("sent_pct_neutro", "% Sentenças Neutras", 16, "sentiment"),
            ColumnSpec("sent_n_sentencas", "Nº de Sentenças", 12, "sentiment"),
        ]

    def run(self, ctx: DocumentContext) -> Dict[str, object]:
        engine = self._analyzer()
        sentences: List[Dict[str, object]] = []
        compounds: List[float] = []
        counts = {POSITIVE: 0, NEGATIVE: 0, NEUTRAL: 0}

        for page in ctx.analytical_page_numbers:
            page_text = ctx.pages_text[page - 1]
            for sentence in segment_sentences(page_text):
                compound = engine.polarity_scores(sentence)["compound"]
                klass = classify(compound)
                counts[klass] += 1
                compounds.append(compound)
                sentences.append(
                    {
                        "page": page,
                        "text": sentence,
                        "compound": compound,
                        "classe": klass,
                    }
                )

        n = len(sentences)
        if n == 0:
            return {
                "sent_classe": NEUTRAL,
                "sent_compound_medio": 0.0,
                "sent_pct_positivo": 0.0,
                "sent_pct_negativo": 0.0,
                "sent_pct_neutro": 0.0,
                "sent_n_sentencas": 0,
                "sentiment_sentences": [],
            }

        mean_compound = round(sum(compounds) / n, 4)
        return {
            "sent_classe": classify(mean_compound),
            "sent_compound_medio": mean_compound,
            "sent_pct_positivo": round(100 * counts[POSITIVE] / n, 1),
            "sent_pct_negativo": round(100 * counts[NEGATIVE] / n, 1),
            "sent_pct_neutro": round(100 * counts[NEUTRAL] / n, 1),
            "sent_n_sentencas": n,
            "sentiment_sentences": sentences,
        }
