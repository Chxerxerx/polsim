from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from polsim.core.sim import Simulation
from polsim.save import SaveError, load_game, save_game


def _exercise(sim: Simulation) -> None:
    """Give the simulation non-trivial state worth round-tripping."""
    sim.rng.stream("test.alpha").random(64)
    sim.rng.stream("test.beta").integers(0, 100, size=32)
    for _ in range(4):
        sim.ids.allocate("event")
    sim.ids.allocate("party")
    for _ in range(6):
        sim.advance_week()


def test_round_trip_preserves_state_hash(sim: Simulation, tmp_path: Path) -> None:
    _exercise(sim)
    path = tmp_path / "world.sqlite"
    save_game(sim, path)
    loaded = load_game(path)
    assert loaded.state_hash() == sim.state_hash()


def test_round_trip_preserves_future_randomness(sim: Simulation, tmp_path: Path) -> None:
    _exercise(sim)
    path = tmp_path / "world.sqlite"
    save_game(sim, path)
    expected = sim.rng.stream("test.alpha").random(16).tolist()
    loaded = load_game(path)
    assert loaded.rng.stream("test.alpha").random(16).tolist() == expected


def test_resave_over_existing_file(sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "world.sqlite"
    save_game(sim, path)
    _exercise(sim)
    save_game(sim, path)
    assert load_game(path).state_hash() == sim.state_hash()


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(SaveError):
        load_game(tmp_path / "nope.sqlite")


def test_corrupt_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "garbage.sqlite"
    path.write_bytes(b"this is definitely not a sqlite database")
    with pytest.raises(SaveError):
        load_game(path)


def test_newer_schema_raises(sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite"
    save_game(sim, path)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE meta SET value = '99' WHERE key = 'schema_version'")
    with pytest.raises(SaveError):
        load_game(path)
