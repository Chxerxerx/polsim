"""Weighted aggregates and incremental cache invalidation (M2)."""

from __future__ import annotations

import numpy as np
import pytest
from tests.conftest import small_sim

from polsim.people.columns import EDUCATION_LEVELS


def test_weighted_mean_matches_numpy() -> None:
    sim = small_sim()
    means = sim.aggregates.weighted_mean("income")
    district_id = sim.population.district_ids()[0]
    values = sim.population.district_column(district_id, "income").astype(np.float64)
    weights = sim.population.district_column(district_id, "population_weight")
    expected = float((values * weights).sum() / weights.sum())
    assert means[district_id] == pytest.approx(expected)


def test_category_counts_sum_to_population() -> None:
    sim = small_sim()
    counts = sim.aggregates.category_counts("education", len(EDUCATION_LEVELS))
    populations = sim.aggregates.weighted_population()
    for district_id, values in counts.items():
        assert int(values.sum()) == populations[district_id]


def test_national_population_matches_scenario() -> None:
    sim = small_sim()
    assert sim.aggregates.national_population() == sim.scenario.represented_population


def test_cache_recomputes_only_dirty_districts() -> None:
    sim = small_sim()
    districts = len(sim.population.district_ids())
    sim.aggregates.weighted_mean("income")
    assert sim.aggregates.recompute_count == districts
    sim.aggregates.weighted_mean("income")  # fully cached
    assert sim.aggregates.recompute_count == districts
    touched = sim.population.district_ids()[3]
    sim.population.add_district_values(touched, "income", 1.0)
    before = sim.aggregates.weighted_mean("income")[touched]
    assert sim.aggregates.recompute_count == districts + 1  # only the dirty district
    sim.population.add_district_values(touched, "income", 1.0)
    after = sim.aggregates.weighted_mean("income")[touched]
    assert after == pytest.approx(before + 1.0)
