"""Game and scenario configuration (Milestone 1).

Only settings that current or next-milestone systems consume are defined
(no invented requirements). ``simulated_citizen_target`` implements the
specification section 6.1 requirement that the ~250,000-citizen default be
configurable; population generation consumes it from Milestone 2.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from datetime import date
from typing import Any

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class ConfigError(ValueError):
    """Raised when a configuration mapping is invalid."""


def _reject_unknown_keys(cls: type, data: Mapping[str, object]) -> None:
    unknown = set(data) - {field.name for field in fields(cls)}
    if unknown:
        raise ConfigError(f"unknown {cls.__name__} keys: {sorted(unknown)}")


@dataclass(frozen=True)
class GameConfig:
    """Player-adjustable technical game settings."""

    simulated_citizen_target: int = 250_000
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if self.simulated_citizen_target < 1:
            raise ConfigError("simulated_citizen_target must be positive")
        if self.log_level not in _LOG_LEVELS:
            raise ConfigError(f"log_level must be one of {_LOG_LEVELS}")

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> GameConfig:
        _reject_unknown_keys(cls, data)
        target = data.get("simulated_citizen_target", 250_000)
        level = data.get("log_level", "INFO")
        if isinstance(target, bool) or not isinstance(target, int):
            raise ConfigError("simulated_citizen_target must be an integer")
        if not isinstance(level, str):
            raise ConfigError("log_level must be a string")
        return cls(simulated_citizen_target=target, log_level=level)


@dataclass(frozen=True)
class ScenarioConfig:
    """Identity and top-level parameters of the selected scenario."""

    scenario_id: str
    name: str
    start_date: date
    represented_population: int
    parliament_seats: int

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.name:
            raise ConfigError("scenario_id and name must be non-empty")
        if self.represented_population < 1:
            raise ConfigError("represented_population must be positive")
        if self.parliament_seats < 1:
            raise ConfigError("parliament_seats must be positive")

    def snapshot(self) -> dict[str, Any]:
        data = asdict(self)
        data["start_date"] = self.start_date.isoformat()
        return data

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> ScenarioConfig:
        _reject_unknown_keys(cls, data)
        scenario_id = data.get("scenario_id")
        name = data.get("name")
        start = data.get("start_date")
        population = data.get("represented_population")
        seats = data.get("parliament_seats")
        if not isinstance(scenario_id, str) or not isinstance(name, str):
            raise ConfigError("scenario_id and name must be strings")
        if not isinstance(start, str):
            raise ConfigError("start_date must be an ISO date string")
        if isinstance(population, bool) or not isinstance(population, int):
            raise ConfigError("represented_population must be an integer")
        if isinstance(seats, bool) or not isinstance(seats, int):
            raise ConfigError("parliament_seats must be an integer")
        try:
            parsed_start = date.fromisoformat(start)
        except ValueError as exc:
            raise ConfigError(f"invalid start_date: {start!r}") from exc
        return cls(
            scenario_id=scenario_id,
            name=name,
            start_date=parsed_start,
            represented_population=population,
            parliament_seats=seats,
        )

    @classmethod
    def default(cls) -> ScenarioConfig:
        """The approved default MVP scenario shape (ADR-005)."""
        return cls(
            scenario_id="default-republic",
            name="Fictional Parliamentary Republic (working scenario)",
            start_date=date(2026, 1, 5),
            represented_population=10_000_000,
            parliament_seats=200,
        )
