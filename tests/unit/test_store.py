"""Population store: validation, updates, revisions, dirty tracking (M2)."""

from __future__ import annotations

import numpy as np
import pytest
from tests.conftest import small_sim

from polsim.people.columns import column_dtypes
from polsim.people.store import PopulationStore


def _tiny_columns(count: int) -> dict[str, np.ndarray]:
    return {name: np.zeros(count, dtype=dtype) for name, dtype in column_dtypes().items()}


def test_store_validates_columns_and_ranges() -> None:
    columns = _tiny_columns(10)
    with pytest.raises(ValueError):
        PopulationStore(columns, {1: (0, 4)})  # ranges cover 4 of 10 rows
    bad = dict(columns)
    del bad["income"]
    with pytest.raises(ValueError):
        PopulationStore(bad, {1: (0, 10)})


def test_updates_bump_revisions_and_dirty() -> None:
    store = PopulationStore(_tiny_columns(10), {1: (0, 6), 2: (6, 4)})
    store.mark_saved(store.district_ids())
    assert store.dirty_districts() == []
    store.add_district_values(2, "income", 5.0)
    assert store.dirty_districts() == [2]
    assert store.revision(2) == 1
    assert store.revision(1) == 0
    assert float(store.district_column(2, "income").sum()) == 20.0
    assert float(store.district_column(1, "income").sum()) == 0.0
    store.mark_saved([2])
    assert store.dirty_districts() == []


def test_set_district_values() -> None:
    store = PopulationStore(_tiny_columns(8), {1: (0, 8)})
    store.set_district_values(1, "health", 0.5)
    assert float(store.column("health").mean()) == pytest.approx(0.5)


def test_new_world_is_fully_dirty_until_saved() -> None:
    sim = small_sim()
    assert sim.population.dirty_districts() == sim.population.district_ids()
