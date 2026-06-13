"""LeIA — Léxico para Inferência Adaptada (vendored).

Fork of VADER (Valence Aware Dictionary and sEntiment Reasoner) adapted to
Brazilian Portuguese.

Upstream:  https://github.com/rafjaa/LeIA
VADER:     https://github.com/cjhutto/vaderSentiment (C.J. Hutto)
License:   MIT — see LICENSE.txt in this directory.

Citation (method):
    Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious Rule-based Model
    for Sentiment Analysis of Social Media Text. Eighth International Conference
    on Weblogs and Social Media (ICWSM-14). Ann Arbor, MI, June 2014.
    Portuguese adaptation: Almeida, R. J. de A. LeIA - Léxico para Inferência
    Adaptada. https://github.com/rafjaa/LeIA
"""

from .leia import SentimentIntensityAnalyzer

__all__ = ["SentimentIntensityAnalyzer"]
