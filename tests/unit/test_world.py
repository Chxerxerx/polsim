"""World generation: structure, determinism, weights, demographics (M2)."""

from __future__ import annotations

import numpy as np
from tests.conftest import small_sim

from polsim.people.columns import EMPLOYMENT_STATUSES
from polsim.world.model import World


def test_same_seed_generates_identical_world() -> None:
    first = small_sim()
    second = small_sim()
    assert first.world.to_json_dict() == second.world.to_json_dict()
    assert first.population.column_hashes() == second.population.column_hashes()
    assert first.state_hash() == second.state_hash()


def test_different_seeds_generate_different_worlds() -> None:
    assert small_sim(1).state_hash() != small_sim(2).state_hash()


def test_geography_structure(sim_world: None = None) -> None:
    sim = small_sim()
    world = sim.world
    province_ids = {province.province_id for province in world.provinces}
    district_ids = {district.district_id for district in world.districts}
    assert len(world.provinces) == 10
    assert len(world.districts) == 32
    assert all(district.province_id in province_ids for district in world.districts)
    assert all(town.district_id in district_ids for town in world.towns)
    # Every province has at least one district; every district at least one urban town.
    assert {district.province_id for district in world.districts} == province_ids
    for district_id in district_ids:
        assert any(
            town.urban for town in world.towns if town.district_id == district_id
        )


def test_world_json_round_trip() -> None:
    world = small_sim().world
    assert World.from_json_dict(world.to_json_dict()) == world


def test_population_weights_conserved_exactly() -> None:
    sim = small_sim()
    weights = sim.population.column("population_weight")
    assert sim.population.count == 2500
    assert int(weights.sum()) == sim.scenario.represented_population
    assert int(weights.min()) >= 1
    # Per-district conservation against the aggregate system.
    per_district = sim.aggregates.weighted_population()
    for district_id, (start, length) in sim.population.district_ranges().items():
        assert per_district[district_id] == int(weights[start : start + length].sum())


def test_citizen_geography_is_consistent() -> None:
    sim = small_sim()
    town_district = {town.town_id: town.district_id for town in sim.world.towns}
    town_urban = {town.town_id: int(town.urban) for town in sim.world.towns}
    district_province = {
        district.district_id: district.province_id for district in sim.world.districts
    }
    towns = sim.population.column("town")
    districts = sim.population.column("district")
    provinces = sim.population.column("province")
    urban = sim.population.column("urban")
    for row in range(0, sim.population.count, 97):  # sample rows
        assert town_district[int(towns[row])] == int(districts[row])
        assert district_province[int(districts[row])] == int(provinces[row])
        assert town_urban[int(towns[row])] == int(urban[row])
    # Rows are sorted by district (chunk alignment).
    assert bool(np.all(np.diff(districts) >= 0))


def test_demographics_are_sane() -> None:
    sim = small_sim()
    store = sim.population
    age_weeks = -store.column("birth_week")
    assert int(age_weeks.min()) >= 0
    assert float(age_weeks.max()) / 52.0 < 100.0
    assert float(store.column("income").min()) >= 0.0
    assert float(store.column("wealth").min()) >= 0.0
    assert float(store.column("health").min()) >= 0.0
    assert float(store.column("health").max()) <= 1.0
    child = EMPLOYMENT_STATUSES.index("child")
    minors = age_weeks < 15 * 52
    assert bool(np.all(store.column("employment")[minors] == child))
    assert bool(np.all(store.column("income")[minors] == 0.0))
    # Name indices stay inside the pools.
    assert int(store.column("given_name").max()) < len(sim.world.given_names)
    assert int(store.column("family_name").max()) < len(sim.world.family_names)
