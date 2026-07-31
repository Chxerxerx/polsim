from __future__ import annotations

import pytest

from polsim.core.rng import RngManager


def test_same_seed_same_stream_sequences() -> None:
    a = RngManager(42)
    b = RngManager(42)
    assert a.stream("x").integers(0, 10**9, size=16).tolist() == b.stream("x").integers(
        0, 10**9, size=16
    ).tolist()


def test_streams_are_independent() -> None:
    manager = RngManager(42)
    first = manager.stream("alpha").integers(0, 10**9, size=16).tolist()
    second = manager.stream("beta").integers(0, 10**9, size=16).tolist()
    assert first != second


def test_different_seeds_diverge() -> None:
    assert (
        RngManager(1).stream("x").integers(0, 10**9, size=16).tolist()
        != RngManager(2).stream("x").integers(0, 10**9, size=16).tolist()
    )


def test_snapshot_restore_continues_sequence() -> None:
    manager = RngManager(42)
    manager.stream("x").random(100)  # advance the stream
    state = manager.snapshot()
    expected = manager.stream("x").random(50).tolist()

    restored = RngManager(42)
    restored.restore(state)
    assert restored.stream("x").random(50).tolist() == expected


def test_stream_creation_order_does_not_matter() -> None:
    forward = RngManager(7)
    forward.stream("a")
    values_b = forward.stream("b").random(8).tolist()

    reverse = RngManager(7)
    reverse.stream("b")
    assert reverse.stream("b").random(8).tolist() == values_b


@pytest.mark.parametrize("bad_seed", [-1, 2**64])
def test_seed_range_enforced(bad_seed: int) -> None:
    with pytest.raises(ValueError):
        RngManager(bad_seed)
