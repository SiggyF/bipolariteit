"""
Ruwe tekststatistieken van een sprekerbeurt (documents.content), berekend
voor persistente opslag als JSON op documents.text_stats (issue #155).

Alleen ruwe tellingen worden opgeslagen (word_count, sentence_count,
syllable_count, long_word_count, unique_word_count, token_count) -- de
afgeleide leesbaarheidsindices (Flesch-Douma, LIX, TTR) blijven pure
functies over die tellingen, zodat een latere formulewijziging nooit een
her-backfill vergt of tot drift met opgeslagen waarden leidt.

Lettergreeptelling is een vocaal-groepen-heuristiek (geen echte NL-
hyphenator), dus Flesch-Douma en LIX zijn indicatief, geen exacte score.
"""

import re

import tiktoken

_WOORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_ZIN_SPLIT_RE = re.compile(r"[.!?]+(?:\s+|$)")
_VOCAAL_GROEP_RE = re.compile(r"[aeiouyàáâäèéêëìíîïòóôöùúûü]+", re.IGNORECASE)
_ENCODING = tiktoken.get_encoding("o200k_base")


def _zinnen(tekst):
    kandidaten = [z.strip() for z in _ZIN_SPLIT_RE.split(tekst)]
    return [z for z in kandidaten if _WOORD_RE.search(z)]


def _lettergrepen(woord):
    # Vocaal-groepen-heuristiek: elke aaneengesloten reeks klinkers telt als
    # één lettergreep. Geen echte NL-hyphenator, maar voldoende voor een
    # grove, snelle indicatie zonder externe dependency.
    return max(1, len(_VOCAAL_GROEP_RE.findall(woord)))


def compute_document_stats(content):
    """Ruwe tekststatistieken voor persistente opslag als JSON op
    documents.text_stats."""
    woorden = _WOORD_RE.findall(content)
    zinnen = _zinnen(content)
    return {
        "word_count": len(woorden),
        "sentence_count": len(zinnen) or 1,
        "syllable_count": sum(_lettergrepen(w) for w in woorden),
        "long_word_count": sum(1 for w in woorden if len(w) > 6),
        "unique_word_count": len({w.lower() for w in woorden}),
        "token_count": len(_ENCODING.encode(content)),
    }


def flesch_douma(word_count, sentence_count, syllable_count):
    if word_count == 0 or sentence_count == 0:
        return 0.0
    gem_zinslengte = word_count / sentence_count
    gem_lettergrepen_per_woord = syllable_count / word_count
    return 206.84 - 0.93 * gem_zinslengte - 77 * gem_lettergrepen_per_woord


def lix(word_count, sentence_count, long_word_count):
    if word_count == 0 or sentence_count == 0:
        return 0.0
    gem_zinslengte = word_count / sentence_count
    return gem_zinslengte + (long_word_count * 100 / word_count)


def ttr(word_count, unique_word_count):
    if word_count == 0:
        return 0.0
    return unique_word_count / word_count
