from __future__ import annotations

import pytest

from polsim.core.rng import MAX_SEED
from polsim.core.seed import format_seed, generate_world_seed, parse_seed


@pytest.mark.parametrize("seed", [0, 1, 31, 32, 2**32, MAX_SEED, 1234567890123456789])
def test_format_parse_round_trip(seed: int) -> None:
    assert parse_seed(format_seed(seed)) == seed


def test_decimal_form_accepted() -> None:
    assert parse_seed("123456789") == 123456789


def test_confusable_characters_mapped() -> None:
    canonical = format_seed(1234567890123456789)
    mangled = canonical.lower().replace("0", "o").replace("1", "l")
    assert parse_seed(mangled) == 1234567890123456789


@pytest.mark.parametrize("bad", ["", "hello world!", "ZZZZ-ZZZZ-ZZZZ-Z"])
def test_invalid_forms_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_seed(bad)


def test_generated_seed_in_range() -> None:
    for _ in range(8):
        assert 0 <= generate_world_seed() <= MAX_SEED
