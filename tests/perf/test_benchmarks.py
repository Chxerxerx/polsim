"""Performance benchmark infrastructure (Milestone 1; design doc 04).

These establish the benchmark harness and Milestone-1 baselines. Budgeted
operations from design doc 04 gain real workloads as their systems land
(population at M2, voting at M5). CI tracks trends; acceptance against the
budget table is measured on target-class hardware.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polsim.core.sim import Simulation
from polsim.save import load_game, save_game

SEED = 42


def _loaded_sim() -> Simulation:
    sim = Simulation.new_game(world_seed=SEED)
    for name in ("bench.a", "bench.b", "bench.c"):
        sim.rng.stream(name).random(256)
    for _ in range(100):
        sim.ids.allocate("event")
    return sim


def test_bench_advance_week(benchmark: Any) -> None:
    sim = _loaded_sim()
    benchmark(sim.advance_week)


def test_bench_state_hash(benchmark: Any) -> None:
    sim = _loaded_sim()
    benchmark(sim.state_hash)


def test_bench_save(benchmark: Any, tmp_path: Path) -> None:
    sim = _loaded_sim()
    path = tmp_path / "bench.sqlite"
    benchmark(lambda: save_game(sim, path))


def test_bench_load(benchmark: Any, tmp_path: Path) -> None:
    sim = _loaded_sim()
    path = tmp_path / "bench.sqlite"
    save_game(sim, path)
    benchmark(lambda: load_game(path))
