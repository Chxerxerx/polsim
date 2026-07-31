"""New-game world-seed generation and display formatting (Milestone 1).

Drawing entropy from the operating system here is the single sanctioned
non-deterministic point in the simulation (design doc 03): everything after
world creation derives from the stored seed. Seeds are stored in the save,
shown to the player, and shareable (specification section 31.1).
"""

from __future__ import annotations

import secrets

from polsim.core.rng import MAX_SEED

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32: no I, L, O, U
_CHARS = 13  # 13 * 5 bits = 65 bits, covers 64-bit seeds
_GROUP = 4
_CONFUSABLES = str.maketrans({"I": "1", "L": "1", "O": "0"})


def generate_world_seed() -> int:
    """Generate a fresh unsigned 64-bit world seed from OS entropy."""
    return secrets.randbits(64)


def format_seed(seed: int) -> str:
    """Format a seed for display and sharing, e.g. ``0ABC-DEFG-HJK1-2``."""
    if not 0 <= seed <= MAX_SEED:
        raise ValueError("seed must fit in an unsigned 64-bit integer")
    chars = []
    value = seed
    for _ in range(_CHARS):
        chars.append(_ALPHABET[value & 31])
        value >>= 5
    text = "".join(reversed(chars))
    return "-".join(text[i : i + _GROUP] for i in range(0, len(text), _GROUP))


def parse_seed(text: str) -> int:
    """Parse a seed from display form or from a plain decimal integer."""
    cleaned = text.strip().upper().replace("-", "").replace(" ", "")
    cleaned = cleaned.translate(_CONFUSABLES)
    if len(cleaned) == _CHARS and all(char in _ALPHABET for char in cleaned):
        value = 0
        for char in cleaned:
            value = (value << 5) | _ALPHABET.index(char)
    elif cleaned.isdigit():
        value = int(cleaned)
    else:
        raise ValueError(f"unrecognized seed format: {text!r}")
    if value > MAX_SEED:
        raise ValueError("seed out of range")
    return value
