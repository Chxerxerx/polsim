from __future__ import annotations

from datetime import date

import pytest

from polsim.core.clock import SimClock


def test_advance_moves_one_week() -> None:
    clock = SimClock(start_date=date(2026, 1, 5))
    assert clock.week == 0
    assert clock.current_date == date(2026, 1, 5)
    clock.advance()
    clock.advance()
    assert clock.week == 2
    assert clock.current_date == date(2026, 1, 19)


def test_snapshot_round_trip() -> None:
    clock = SimClock(start_date=date(2026, 1, 5), week=7)
    restored = SimClock.from_snapshot(clock.snapshot())
    assert restored == clock


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"start_date": "2026-01-05"},
        {"start_date": 5, "week": 1},
        {"start_date": "2026-01-05", "week": -1},
    ],
)
def test_bad_snapshot_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        SimClock.from_snapshot(bad)
