"""Cached population aggregates with incremental recalculation (M2).

Aggregates are computed per district and cached against the store's
district revision counters: querying recomputes only districts whose
revision changed since the cached value (design docs 02/04). All aggregates
are population-weighted — a simulated citizen counts as
``population_weight`` residents.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from polsim.people.store import PopulationStore

Array = NDArray[Any]


class PopulationAggregates:
    """Weighted per-district aggregates over a :class:`PopulationStore`."""

    def __init__(self, store: PopulationStore) -> None:
        self._store = store
        self._cache: dict[tuple[str, ...], dict[int, tuple[int, Any]]] = {}
        self.recompute_count = 0  # test/profiling metric

    def _per_district(self, key: tuple[str, ...], compute: Any) -> dict[int, Any]:
        cached = self._cache.setdefault(key, {})
        result: dict[int, Any] = {}
        for district_id in self._store.district_ids():
            revision = self._store.revision(district_id)
            entry = cached.get(district_id)
            if entry is None or entry[0] != revision:
                value = compute(district_id)
                cached[district_id] = (revision, value)
                self.recompute_count += 1
            result[district_id] = cached[district_id][1]
        return result

    def weighted_population(self) -> dict[int, int]:
        """Represented residents per district (sum of citizen weights)."""

        def compute(district_id: int) -> int:
            weights = self._store.district_column(district_id, "population_weight")
            return int(weights.sum())

        return self._per_district(("weighted_population",), compute)

    def weighted_mean(self, column: str) -> dict[int, float]:
        """Population-weighted mean of a numeric column per district."""

        def compute(district_id: int) -> float:
            values = self._store.district_column(district_id, column)
            weights = self._store.district_column(district_id, "population_weight")
            total = float(weights.sum())
            return float((values.astype(np.float64) * weights).sum() / total)

        return self._per_district(("weighted_mean", column), compute)

    def category_counts(self, column: str, categories: int) -> dict[int, Array]:
        """Weighted resident counts per category value, per district."""

        def compute(district_id: int) -> Array:
            values = self._store.district_column(district_id, column).astype(np.int64)
            weights = self._store.district_column(district_id, "population_weight")
            return np.bincount(values, weights=weights, minlength=categories).astype(np.int64)

        return self._per_district(("category_counts", column), compute)

    def national_population(self) -> int:
        return sum(self.weighted_population().values())

    def national_mean(self, column: str) -> float:
        populations = self.weighted_population()
        means = self.weighted_mean(column)
        total = sum(populations.values())
        return sum(means[d] * populations[d] for d in populations) / total
