"""Simulation composition root (Milestones 1-2).

Composes configuration, the weekly clock, RNG streams, identifiers, the
generated world, and the citizen population into one deterministic
simulation object. The weekly turn still advances the clock only; the
plan-then-resolve phases of ADR-004 attach here from Milestone 3 onward
(citizen age is derived from birth week and the clock, so aging needs no
weekly column writes). ``state_hash`` covers all persistent state and
drives the replay harness (design doc 03).
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
from polsim.people.aggregates import PopulationAggregates
from polsim.people.characters import CharacterRegistry
from polsim.people.store import PopulationStore
from polsim.politics.generation import generate_politics
from polsim.politics.registry import PoliticalRegistry
from polsim.world.generation import generate_world
from polsim.world.model import World

_LOG = logging.getLogger("polsim.core.sim")


class Simulation:
    """One running world: configuration, clock, RNG, ids, world, citizens."""

    def __init__(
        self,
        game_config: GameConfig,
        scenario: ScenarioConfig,
        world_seed: int,
        world: World,
        population: PopulationStore,
        ids: IdRegistry,
        rng: RngManager,
        characters: CharacterRegistry,
        politics: PoliticalRegistry,
    ) -> None:
        self.game_config = game_config
        self.scenario = scenario
        self.world_seed = world_seed
        self.world = world
        self.population = population
        self.ids = ids
        self.rng = rng
        self.characters = characters
        self.politics = politics
        self.clock = SimClock(start_date=scenario.start_date)
        self.aggregates = PopulationAggregates(population)

    @classmethod
    def new_game(
        cls,
        game_config: GameConfig | None = None,
        scenario: ScenarioConfig | None = None,
        world_seed: int | None = None,
    ) -> Simulation:
        """Start a new world, generating a seed unless one is supplied."""
        seed = generate_world_seed() if world_seed is None else world_seed
        config = game_config or GameConfig()
        scenario_config = scenario or ScenarioConfig.default()
        rng = RngManager(seed)
        ids = IdRegistry()
        world, population = generate_world(scenario_config, config, rng, ids)
        characters = CharacterRegistry()
        politics = generate_politics(
            world, population, ids, characters, rng.stream("worldgen.politics")
        )
        sim = cls(
            config, scenario_config, seed, world, population, ids, rng, characters, politics
        )
        _LOG.info(
            "new game: scenario=%s seed=%d country=%s citizens=%d",
            scenario_config.scenario_id,
            seed,
            world.country_name,
            population.count,
        )
        return sim

    def advance_week(self) -> None:
        """Advance one weekly turn (clock only until M3; see ADR-004)."""
        self.clock.advance()
        _LOG.debug("advanced to week %d (%s)", self.clock.week, self.clock.current_date)

    def state_hash(self) -> str:
        """Canonical hash of the full persistent state, for replay diffs."""
        payload: dict[str, Any] = {
            "world_seed": self.world_seed,
            "clock": self.clock.snapshot(),
            "rng": self.rng.snapshot(),
            "ids": self.ids.snapshot(),
            "game_config": self.game_config.snapshot(),
            "scenario": self.scenario.snapshot(),
            "world": self.world.to_json_dict(),
            "population": self.population.column_hashes(),
            "district_ranges": {
                str(k): list(v) for k, v in sorted(self.population.district_ranges().items())
            },
            "characters": self.characters.to_json_list(),
            "politics": self.politics.to_json_dict(),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
