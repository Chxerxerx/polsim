"""Deterministic fictional name generation (Milestone 2).

Generates pools of fictional personal and place names from seeded RNG
streams via syllable composition. Pools are stored on the ``World`` (and in
the save), so loaded worlds never depend on regeneration.
"""

from __future__ import annotations

import numpy as np

_ONSETS = (
    "b", "br", "d", "dr", "f", "g", "gr", "h", "k", "kl", "l", "m",
    "n", "p", "r", "s", "st", "t", "tr", "v", "z", "",
)
_VOWELS = ("a", "e", "i", "o", "u", "a", "e", "ia", "ei", "au")
_CODAS = ("", "", "l", "n", "r", "s", "m", "nd", "rt", "sk")
_PLACE_SUFFIXES = ("burg", "stad", "holm", "vik", "dal", "berg", "mark", "field", "haven", "ford")


def _syllable(rng: np.random.Generator) -> str:
    return (
        _ONSETS[int(rng.integers(0, len(_ONSETS)))]
        + _VOWELS[int(rng.integers(0, len(_VOWELS)))]
        + _CODAS[int(rng.integers(0, len(_CODAS)))]
    )


def _word(rng: np.random.Generator, syllables: int) -> str:
    text = "".join(_syllable(rng) for _ in range(syllables))
    return text[:1].upper() + text[1:]


def _unique_words(rng: np.random.Generator, count: int, low: int, high: int) -> list[str]:
    seen: set[str] = set()
    words: list[str] = []
    while len(words) < count:
        word = _word(rng, int(rng.integers(low, high + 1)))
        if len(word) < 3 or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return words


def generate_person_name_pools(
    rng: np.random.Generator, given: int, family: int
) -> tuple[list[str], list[str]]:
    """Generate pools of fictional given and family names."""
    return _unique_words(rng, given, 1, 2), _unique_words(rng, family, 2, 3)


def generate_place_names(rng: np.random.Generator, count: int) -> list[str]:
    """Generate unique fictional place names."""
    bases = _unique_words(rng, count, 1, 2)
    return [
        base + _PLACE_SUFFIXES[int(rng.integers(0, len(_PLACE_SUFFIXES)))]
        if rng.random() < 0.6
        else base
        for base in bases
    ]


def generate_label_names(rng: np.random.Generator, count: int, suffix: str = "") -> list[str]:
    """Generate fictional labels (ethnic groups, religions, languages)."""
    return [base + suffix for base in _unique_words(rng, count, 2, 2)]
