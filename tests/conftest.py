"""Shared test fixtures (Milestones 1-2 test infrastructure).

Functional tests use a small citizen target for speed; the 250k target is
exercised by the performance benchmarks in tests/perf.
"""

from __future__ import annotations

import pytest

from polsim.core.config import GameConfig
from polsim.core.sim import Simulation

FIXED_SEED = 1234567890123456789
SMALL_CONFIG = GameConfig(simulated_citizen_target=2500)


def small_sim(world_seed: int = FIXED_SEED) -> Simulation:
    return Simulation.new_game(game_config=SMALL_CONFIG, world_seed=world_seed)


@pytest.fixture
def sim() -> Simulation:
    """A fresh small-population simulation with a fixed seed."""
    return small_sim()
