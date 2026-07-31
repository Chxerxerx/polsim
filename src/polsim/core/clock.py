"""Weekly simulation clock (Milestone 1).

One turn = one week (specification section 5). The clock tracks the
zero-based turn index and derives the calendar date deterministically from
the scenario start date.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SimClock:
    """Deterministic weekly clock. ``week`` is the zero-based turn index."""

    start_date: date
    week: int = 0

    @property
    def current_date(self) -> date:
        return self.start_date + timedelta(weeks=self.week)

    def advance(self) -> None:
        self.week += 1

    def snapshot(self) -> dict[str, str | int]:
        return {"start_date": self.start_date.isoformat(), "week": self.week}

    @classmethod
    def from_snapshot(cls, data: Mapping[str, object]) -> SimClock:
        start = data.get("start_date")
        week = data.get("week")
        if not isinstance(start, str) or not isinstance(week, int) or week < 0:
            raise ValueError(f"invalid clock snapshot: {data!r}")
        return cls(start_date=date.fromisoformat(start), week=week)
