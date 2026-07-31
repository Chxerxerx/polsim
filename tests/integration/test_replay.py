"""Determinism replay harness (Milestone 1; design doc 03).

Every later milestone extends ``_scripted_week`` with its systems' actions.
The harness proves: same seed => same per-turn state hashes, including with
a save/load cycle in the middle of the run.
"""

from __future__ import annotations

from pathlib import Path

from polsim.core.sim import Simulation
from polsim.save import load_game, save_game

FIXED_SEED = 987654321987654321
WEEKS = 12


def _scripted_week(sim: Simulation, week: int) -> None:
    """One week of scripted activity exercising RNG, ids, and the clock."""
    sim.rng.stream("harness.alpha").integers(0, 1_000_000, size=8)
    sim.rng.stream("harness.beta").random(4)
    if week % 3 == 0:
        sim.ids.allocate("event")
    sim.advance_week()


def _run(sim: Simulation, weeks: int, start: int = 0) -> list[str]:
    hashes = []
    for week in range(start, start + weeks):
        _scripted_week(sim, week)
        hashes.append(sim.state_hash())
    return hashes


def test_same_seed_same_history() -> None:
    first = _run(Simulation.new_game(world_seed=FIXED_SEED), WEEKS)
    second = _run(Simulation.new_game(world_seed=FIXED_SEED), WEEKS)
    assert first == second


def test_save_load_mid_run_changes_nothing(tmp_path: Path) -> None:
    straight = _run(Simulation.new_game(world_seed=FIXED_SEED), WEEKS)

    interrupted = Simulation.new_game(world_seed=FIXED_SEED)
    first_half = _run(interrupted, WEEKS // 2)
    path = tmp_path / "midpoint.sqlite"
    save_game(interrupted, path)
    resumed = load_game(path)
    second_half = _run(resumed, WEEKS - WEEKS // 2, start=WEEKS // 2)

    assert first_half + second_half == straight


def test_different_seeds_diverge() -> None:
    first = _run(Simulation.new_game(world_seed=1), 1)
    second = _run(Simulation.new_game(world_seed=2), 1)
    assert first != second
