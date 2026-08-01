"""Struct-of-arrays population store (Milestone 2).

Ordinary citizens are rows across NumPy column arrays (design doc 02),
sorted by electoral district so each district occupies one contiguous row
range — the unit of save chunking (ADR-002) and of dirty tracking.

Event-driven updates: writes go through the district-scoped methods, which
bump that district's revision counter. Dirty districts (revision newer than
the last save) drive incremental saves; aggregate caches compare revisions
to reuse clean districts (design doc 04).

Citizen identifiers equal row index + 1 and are stable: rows are never
reordered or reused (removal, when life simulation arrives, will tombstone).
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from numpy.typing import NDArray

from polsim.people.columns import column_dtypes

Array = NDArray[Any]


class PopulationStore:
    """Columnar citizen storage with district ranges and revision tracking."""

    def __init__(
        self, columns: dict[str, Array], district_ranges: dict[int, tuple[int, int]]
    ) -> None:
        expected = set(column_dtypes())
        if set(columns) != expected:
            missing = sorted(expected - set(columns))
            extra = sorted(set(columns) - expected)
            raise ValueError(f"column mismatch: missing={missing} extra={extra}")
        counts = {len(array) for array in columns.values()}
        if len(counts) != 1:
            raise ValueError(f"inconsistent column lengths: {sorted(counts)}")
        dtypes = column_dtypes()
        self._columns = {
            name: np.ascontiguousarray(array, dtype=dtypes[name])
            for name, array in columns.items()
        }
        self.count = counts.pop()
        span = sum(length for _, length in district_ranges.values())
        if span != self.count:
            raise ValueError(f"district ranges cover {span} rows, store has {self.count}")
        self._ranges = dict(district_ranges)
        self._revision: dict[int, int] = dict.fromkeys(self._ranges, 0)
        self._saved_revision: dict[int, int] = dict.fromkeys(self._ranges, -1)

    # -- structure ---------------------------------------------------------

    def district_ids(self) -> list[int]:
        return sorted(self._ranges)

    def district_range(self, district_id: int) -> tuple[int, int]:
        return self._ranges[district_id]

    def district_ranges(self) -> dict[int, tuple[int, int]]:
        return dict(self._ranges)

    def district_slice(self, district_id: int) -> slice:
        start, length = self._ranges[district_id]
        return slice(start, start + length)

    def column(self, name: str) -> Array:
        """Full column array. Treat as read-only; write via district methods."""
        return self._columns[name]

    def district_column(self, district_id: int, name: str) -> Array:
        return self._columns[name][self.district_slice(district_id)]

    # -- event-driven updates ---------------------------------------------

    def set_district_values(
        self, district_id: int, name: str, values: Array | float | int
    ) -> None:
        self._columns[name][self.district_slice(district_id)] = values
        self._revision[district_id] += 1

    def add_district_values(
        self, district_id: int, name: str, delta: Array | float | int
    ) -> None:
        self._columns[name][self.district_slice(district_id)] += delta
        self._revision[district_id] += 1

    def set_full_column(self, name: str, values: Array) -> None:
        """Overwrite an entire column (bulk generation); dirties every district."""
        if len(values) != self.count:
            raise ValueError(f"column length {len(values)} != store size {self.count}")
        self._columns[name][:] = values
        for district_id in self._revision:
            self._revision[district_id] += 1

    # -- revisions, dirty tracking, hashing --------------------------------

    def revision(self, district_id: int) -> int:
        return self._revision[district_id]

    def dirty_districts(self) -> list[int]:
        return sorted(
            district
            for district, revision in self._revision.items()
            if revision != self._saved_revision[district]
        )

    def mark_saved(self, district_ids: list[int]) -> None:
        for district_id in district_ids:
            self._saved_revision[district_id] = self._revision[district_id]

    def column_hashes(self) -> dict[str, str]:
        return {
            name: hashlib.sha256(array.tobytes()).hexdigest()
            for name, array in sorted(self._columns.items())
        }
