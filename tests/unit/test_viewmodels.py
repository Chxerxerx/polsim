"""Snapshot view-models (Qt-free; M2.5)."""

from __future__ import annotations

from tests.conftest import small_sim

from polsim.ui.viewmodels import build_snapshot


def test_snapshot_matches_simulation_state() -> None:
    sim = small_sim()
    snapshot = build_snapshot(sim)
    assert snapshot.country_name == sim.world.country_name
    assert snapshot.week == 0
    assert snapshot.date_iso == sim.scenario.start_date.isoformat()
    assert snapshot.citizen_count == sim.population.count
    assert snapshot.represented_population == sim.scenario.represented_population
    assert len(snapshot.districts) == len(sim.world.districts)
    populations = sim.aggregates.weighted_population()
    for view in snapshot.districts:
        assert view.population == populations[view.district_id]
        assert len(view.shape) >= 3
        assert 0.0 <= view.urban_share <= 1.0
    assert snapshot.district(snapshot.districts[0].district_id) is not None
    assert snapshot.district(999_999) is None


def test_snapshot_reflects_advancing_weeks() -> None:
    sim = small_sim()
    sim.advance_week()
    sim.advance_week()
    snapshot = build_snapshot(sim)
    assert snapshot.week == 2
