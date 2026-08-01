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


def test_incremental_save_rewrites_only_dirty_chunks(sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "world.sqlite"
    save_game(sim, path)

    def checksums() -> dict[tuple[int, str], str]:
        with sqlite3.connect(path) as conn:
            rows = conn.execute(
                "SELECT district_id, column, checksum FROM population_chunks"
            ).fetchall()
        return {(int(d), str(c)): str(s) for d, c, s in rows}

    before = checksums()
    touched = sim.population.district_ids()[2]
    sim.population.add_district_values(touched, "income", 3.0)
    written = save_game(sim, path, incremental=True)
    assert written == [touched]
    after = checksums()
    changed = {key for key in before if before[key] != after[key]}
    assert changed == {(touched, "income")} | {
        key for key in changed if key[0] == touched
    }  # only the touched district differs
    assert all(key[0] == touched for key in changed)
    loaded = load_game(path)
    assert loaded.state_hash() == sim.state_hash()


def test_incremental_save_requires_matching_world(sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "world.sqlite"
    with pytest.raises(SaveError):
        save_game(sim, path, incremental=True)  # no existing file
    save_game(sim, path)
    from tests.conftest import small_sim

    other = small_sim(world_seed=42)
    with pytest.raises(SaveError):
        save_game(other, path, incremental=True)


def test_corrupt_population_chunk_raises(sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "world.sqlite"
    save_game(sim, path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE population_chunks SET data = X'00112233' WHERE rowid = "
            "(SELECT rowid FROM population_chunks LIMIT 1)"
        )
    with pytest.raises(SaveError):
        load_game(path)


def test_pre_world_schema_rejected_clearly(sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite"
    save_game(sim, path)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE meta SET value = '1' WHERE key = 'schema_version'")
    with pytest.raises(SaveError, match="predates world generation"):
        load_game(path)


def test_political_registries_round_trip(sim: Simulation, tmp_path: Path) -> None:
    path = tmp_path / "politics.sqlite"
    save_game(sim, path)
    loaded = load_game(path)
    assert loaded.politics.canonical_json() == sim.politics.canonical_json()
    assert loaded.characters.to_json_list() == sim.characters.to_json_list()
