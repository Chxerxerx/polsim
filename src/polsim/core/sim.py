"""Simulation composition root (Milestone 1).

Composes the clock, RNG streams, identifier registry, and configuration
into one deterministic simulation object. The weekly turn currently
advances the clock only; the plan-then-resolve phases of ADR-004 attach
here in later milestones. ``state_hash`` supports the replay harness
(design doc 03).
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from polsim.core.clock import SimClock
from polsim.core.config import GameConfig, ScenarioConfig
from polsim.core.ids import IdRegistry
from polsim.core.rng import RngManager
from polsim.core.seed import generate_world_seed

_LOG = logging.getLogger("polsim.core.sim")


class Simulation:
    """One running world: configuration, clock, RNG streams, identifiers."""

    def __init__(
        self, game_config: GameConfig, scenario: ScenarioConfig, world_seed: int
    ) -> None:
        self.game_config = game_config
        self.scenario = scenario
        self.world_seed = world_seed
        self.clock = SimClock(start_date=scenario.start_date)
        self.rng = RngManager(world_seed)
        self.ids = IdRegistry()

    @classmethod
    def new_game(
        cls,
        game_config: GameConfig | None = None,
        scenario: ScenarioConfig | None = None,
        world_seed: int | None = None,
    ) -> Simulation:
        """Start a new world, generating a seed unless one is supplied."""
        seed = generate_world_seed() if world_seed is None else world_seed
        sim = cls(game_config or GameConfig(), scenario or ScenarioConfig.default(), seed)
        _LOG.info("new game: scenario=%s seed=%d", sim.scenario.scenario_id, seed)
        return sim

    def advance_week(self) -> None:
        """Advance one weekly turn (clock only at Milestone 1; see ADR-004)."""
        self.clock.advance()
        _LOG.debug("advanced to week %d (%s)", self.clock.week, self.clock.current_date)

    def state_hash(self) -> str:
        """Canonical hash of the full Milestone-1 state, for replay diffs."""
        payload: dict[str, Any] = {
            "world_seed": self.world_seed,
            "clock": self.clock.snapshot(),
            "rng": self.rng.snapshot(),
            "ids": self.ids.snapshot(),
            "game_config": self.game_config.snapshot(),
            "scenario": self.scenario.snapshot(),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
