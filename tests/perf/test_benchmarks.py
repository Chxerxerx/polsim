"""Performance benchmarks at the 250,000-citizen target (M2 hard gate).

Measures the budgeted operations from design doc 04 at full scale:
world generation, full save, incremental save, load, state hash, a
representative full-population batch update (synthetic workload standing in
for M3+ opinion updates), and aggregate recomputation. CI tracks trends;
gate acceptance numbers are read from a target-class machine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from polsim.core.config import GameConfig
from polsim.core.sim import Simulation
from polsim.save import load_game, save_game

SEED = 42
FULL = GameConfig(simulated_citizen_target=250_000)


@pytest.fixture(scope="module")
def full_sim() -> Simulation:
    return Simulation.new_game(game_config=FULL, world_seed=SEED)


def test_bench_world_generation_250k(benchmark: Any) -> None:
    benchmark.pedantic(
        lambda: Simulation.new_game(game_config=FULL, world_seed=SEED),
        rounds=3,
        iterations=1,
    )


def test_bench_full_save_250k(benchmark: Any, full_sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "bench.sqlite"
    benchmark.pedantic(lambda: save_game(full_sim, path), rounds=3, iterations=1)


def test_bench_incremental_save_250k(
    benchmark: Any, full_sim: Simulation, tmp_path: Path
) -> None:
    path = tmp_path / "bench.sqlite"
    save_game(full_sim, path)
    district = full_sim.population.district_ids()[0]

    def one_dirty_district() -> None:
        full_sim.population.add_district_values(district, "income", 0.01)
        save_game(full_sim, path, incremental=True)

    benchmark.pedantic(one_dirty_district, rounds=3, iterations=1)


def test_bench_load_250k(benchmark: Any, full_sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "bench.sqlite"
    save_game(full_sim, path)
    benchmark.pedantic(lambda: load_game(path), rounds=3, iterations=1)


def test_bench_state_hash_250k(benchmark: Any, full_sim: Simulation) -> None:
    benchmark.pedantic(full_sim.state_hash, rounds=3, iterations=1)


def test_bench_weekly_batch_update_250k(benchmark: Any, full_sim: Simulation) -> None:
    """Synthetic full-population update: touch three float columns per district."""
    store = full_sim.population

    def update_all() -> None:
        for district_id in store.district_ids():
            count = store.district_range(district_id)[1]
            drift = np.float32(0.001)
            store.add_district_values(district_id, "income", drift)
            store.add_district_values(district_id, "wealth", store.district_column(
                district_id, "income") * np.float32(0.0001))
            store.set_district_values(
                district_id, "health", np.clip(
                    store.district_column(district_id, "health"), 0.05, 1.0
                ),
            )
            del count

    benchmark.pedantic(update_all, rounds=3, iterations=1)


def test_bench_aggregate_recompute_250k(benchmark: Any, full_sim: Simulation) -> None:
    def recompute() -> None:
        for district_id in full_sim.population.district_ids():
            full_sim.population.add_district_values(district_id, "income", 0.0)
        full_sim.aggregates.weighted_mean("income")
        full_sim.aggregates.weighted_population()

    benchmark.pedantic(recompute, rounds=3, iterations=1)
