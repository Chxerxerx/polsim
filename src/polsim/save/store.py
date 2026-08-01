"""Save and load on the SQLite hybrid container (Milestone 2, ADR-002).

Schema v2 stores, in one WAL-mode SQLite file: metadata, configuration,
clock, RNG stream states, identifier allocators, the world (JSON), and the
population as zstd-compressed per-district column chunks with per-chunk
checksums. Incremental saves rewrite only districts whose store revision
changed since the last save, plus the (small) non-population state.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import zstandard
from numpy.typing import NDArray

from polsim import __version__
from polsim.core.clock import SimClock
from polsim.core.config import GameConfig, ScenarioConfig
from polsim.core.ids import IdRegistry
from polsim.core.rng import RngManager
from polsim.core.sim import Simulation
from polsim.people.columns import COLUMN_DTYPES
from polsim.people.store import PopulationStore
from polsim.save.migrations import SCHEMA_VERSION, MigrationError, apply_migrations
from polsim.world.model import World

Array = NDArray[Any]

_ZSTD_LEVEL = 3


class SaveError(RuntimeError):
    """Raised when a save file is missing, corrupt, or unreadable."""


_TABLES = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rng_streams (name TEXT PRIMARY KEY, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS id_allocators (domain TEXT PRIMARY KEY, next_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS population_chunks (
    district_id INTEGER NOT NULL,
    column TEXT NOT NULL,
    dtype TEXT NOT NULL,
    count INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    data BLOB NOT NULL,
    PRIMARY KEY (district_id, column)
);
"""


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.DatabaseError as exc:
        conn.close()
        raise SaveError(f"cannot open save file {path}: {exc}") from exc
    return conn


def _write_meta(conn: sqlite3.Connection, sim: Simulation) -> None:
    meta = {
        "schema_version": str(SCHEMA_VERSION),
        "app_version": __version__,
        "world_seed": str(sim.world_seed),
        "clock": json.dumps(sim.clock.snapshot()),
        "game_config": json.dumps(sim.game_config.snapshot()),
        "scenario": json.dumps(sim.scenario.snapshot()),
        "world": json.dumps(sim.world.to_json_dict()),
        "district_ranges": json.dumps(
            {str(k): list(v) for k, v in sorted(sim.population.district_ranges().items())}
        ),
    }
    conn.execute("DELETE FROM meta")
    conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
    conn.execute("DELETE FROM rng_streams")
    conn.executemany("INSERT INTO rng_streams VALUES (?, ?)", sorted(sim.rng.snapshot().items()))
    conn.execute("DELETE FROM id_allocators")
    conn.executemany("INSERT INTO id_allocators VALUES (?, ?)", sorted(sim.ids.snapshot().items()))


def _write_district_chunks(
    conn: sqlite3.Connection, store: PopulationStore, district_ids: list[int]
) -> None:
    compressor = zstandard.ZstdCompressor(level=_ZSTD_LEVEL)
    rows = []
    for district_id in district_ids:
        for column in sorted(COLUMN_DTYPES):
            values = np.ascontiguousarray(store.district_column(district_id, column))
            blob = compressor.compress(values.tobytes())
            rows.append(
                (
                    district_id,
                    column,
                    COLUMN_DTYPES[column],
                    len(values),
                    hashlib.sha256(blob).hexdigest(),
                    blob,
                )
            )
    conn.executemany("INSERT OR REPLACE INTO population_chunks VALUES (?, ?, ?, ?, ?, ?)", rows)


def save_game(sim: Simulation, path: Path, *, incremental: bool = False) -> list[int]:
    """Write state to ``path``; returns the district ids rewritten.

    Full saves rewrite every district chunk. Incremental saves require an
    existing save of the same world at ``path`` and rewrite only districts
    dirty since the last save (plus all non-population state, which is
    small).
    """
    if incremental:
        if not path.exists():
            raise SaveError(f"incremental save requires an existing save: {path}")
        districts = sim.population.dirty_districts()
    else:
        districts = sim.population.district_ids()
    conn = _connect(path)
    try:
        if incremental:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'world_seed'"
            ).fetchone()
            if row is None or int(row[0]) != sim.world_seed:
                raise SaveError(f"incremental save target is a different world: {path}")
        with conn:
            conn.executescript(_TABLES)
            if not incremental:
                conn.execute("DELETE FROM population_chunks")
            _write_meta(conn, sim)
            _write_district_chunks(conn, sim.population, districts)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.DatabaseError as exc:
        raise SaveError(f"failed to write save {path}: {exc}") from exc
    finally:
        conn.close()
    sim.population.mark_saved(districts)
    return districts


def _load_population(
    conn: sqlite3.Connection, district_ranges: dict[int, tuple[int, int]]
) -> PopulationStore:
    total = sum(length for _, length in district_ranges.values())
    columns: dict[str, Array] = {
        name: np.empty(total, dtype=dtype) for name, dtype in COLUMN_DTYPES.items()
    }
    decompressor = zstandard.ZstdDecompressor()
    filled: dict[str, int] = dict.fromkeys(COLUMN_DTYPES, 0)
    cursor = conn.execute(
        "SELECT district_id, column, dtype, count, checksum, data FROM population_chunks"
    )
    for district_id, column, dtype, count, checksum, blob in cursor:
        if column not in COLUMN_DTYPES:
            raise SaveError(f"unknown population column in save: {column!r}")
        if hashlib.sha256(blob).hexdigest() != checksum:
            raise SaveError(f"population chunk corrupt (district {district_id}, {column})")
        if district_id not in district_ranges:
            raise SaveError(f"population chunk for unknown district {district_id}")
        start, length = district_ranges[district_id]
        if count != length:
            raise SaveError(
                f"population chunk length mismatch (district {district_id}, {column})"
            )
        values = np.frombuffer(decompressor.decompress(blob), dtype=dtype)
        if len(values) != length:
            raise SaveError(f"population chunk size mismatch (district {district_id}, {column})")
        columns[column][start : start + length] = values
        filled[column] += length
    incomplete = sorted(name for name, done in filled.items() if done != total)
    if incomplete:
        raise SaveError(f"population data incomplete for columns: {incomplete}")
    return PopulationStore(columns, district_ranges)


def load_game(path: Path) -> Simulation:
    """Load a save, migrating older schemas, verifying integrity first."""
    if not path.exists():
        raise SaveError(f"save file does not exist: {path}")
    conn = _connect(path)
    try:
        row = conn.execute("PRAGMA quick_check").fetchone()
        if row is None or row[0] != "ok":
            raise SaveError(f"integrity check failed: {path}")
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        if "schema_version" not in meta:
            raise SaveError(f"not a polsim save (missing metadata): {path}")
        version = int(meta["schema_version"])
        if version != SCHEMA_VERSION:
            with conn:
                apply_migrations(conn, version)
            meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        game_config = GameConfig.from_mapping(json.loads(meta["game_config"]))
        scenario = ScenarioConfig.from_mapping(json.loads(meta["scenario"]))
        world = World.from_json_dict(json.loads(meta["world"]))
        district_ranges = {
            int(key): (int(value[0]), int(value[1]))
            for key, value in json.loads(meta["district_ranges"]).items()
        }
        population = _load_population(conn, district_ranges)
        rng = RngManager(int(meta["world_seed"]))
        rng.restore(dict(conn.execute("SELECT name, state FROM rng_streams").fetchall()))
        ids = IdRegistry()
        ids.restore(
            {str(d): int(n) for d, n in conn.execute("SELECT domain, next_id FROM id_allocators")}
        )
        sim = Simulation(
            game_config, scenario, int(meta["world_seed"]), world, population, ids, rng
        )
        sim.clock = SimClock.from_snapshot(json.loads(meta["clock"]))
        population.mark_saved(population.district_ids())
        return sim
    except (
        sqlite3.DatabaseError,
        MigrationError,
        KeyError,
        ValueError,
        zstandard.ZstdError,
    ) as exc:
        raise SaveError(f"failed to load save {path}: {exc}") from exc
    finally:
        conn.close()
