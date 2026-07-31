from __future__ import annotations

from datetime import date

import pytest

from polsim.core.config import ConfigError, GameConfig, ScenarioConfig


def test_game_config_defaults_and_round_trip() -> None:
    config = GameConfig()
    assert config.simulated_citizen_target == 250_000
    assert GameConfig.from_mapping(config.snapshot()) == config


def test_game_config_validation() -> None:
    with pytest.raises(ConfigError):
        GameConfig(simulated_citizen_target=0)
    with pytest.raises(ConfigError):
        GameConfig(log_level="LOUD")
    with pytest.raises(ConfigError):
        GameConfig.from_mapping({"citizens": 5})  # unknown key
    with pytest.raises(ConfigError):
        GameConfig.from_mapping({"simulated_citizen_target": True})


def test_default_scenario_matches_adr_005() -> None:
    scenario = ScenarioConfig.default()
    assert scenario.represented_population == 10_000_000
    assert scenario.parliament_seats == 200
    assert scenario.start_date == date(2026, 1, 5)


def test_scenario_round_trip() -> None:
    scenario = ScenarioConfig.default()
    assert ScenarioConfig.from_mapping(scenario.snapshot()) == scenario


@pytest.mark.parametrize(
    "override",
    [
        {"scenario_id": ""},
        {"represented_population": 0},
        {"parliament_seats": 0},
        {"start_date": "not-a-date"},
        {"unknown_key": 1},
    ],
)
def test_scenario_validation(override: dict[str, object]) -> None:
    data = ScenarioConfig.default().snapshot()
    data.update(override)
    with pytest.raises(ConfigError):
        ScenarioConfig.from_mapping(data)
