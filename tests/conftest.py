"""Shared test fixtures (Milestone 1 test infrastructure)."""

from __future__ import annotations

import pytest

from polsim.core.sim import Simulation

FIXED_SEED = 1234567890123456789


@pytest.fixture
def sim() -> Simulation:
    """A fresh simulation with a fixed seed and default configuration."""
    return Simulation.new_game(world_seed=FIXED_SEED)
