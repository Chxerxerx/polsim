"""Basic save and load on the SQLite hybrid container (Milestone 1).

Implements the ADR-002 container for the state that exists today: metadata,
configuration, clock, RNG stream states, and identifier allocators, written
transactionally in WAL mode with an integrity check on load. Population
column chunks and entity tables join in Milestone 2.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from polsim import __version__
from polsim.core.clock import SimClock
from polsim.core.config import GameConfig, ScenarioConfig
from polsim.core.sim import Simulation
from polsim.save.migrations import SCHEMA_VERSION, MigrationError, apply_migrations


class SaveError(RuntimeError):
    """Raised when a save file is missing, corrupt, or unreadable."""


_TABLES = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rng_streams (name TEXT PRIMARY KEY, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS id_allocators (domain TEXT PRIMARY KEY, next_id INTEGER NOT NULL);
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


def save_game(sim: Simulation, path: Path) -> None:
    """Write the full current state to ``path`` transactionally."""
    conn = _connect(path)
    try:
        with conn:
            conn.executescript(_TABLES)
            conn.execute("DELETE FROM meta")
            conn.execute("DELETE FROM rng_streams")
            conn.execute("DELETE FROM id_allocators")
            meta = {
                "schema_version": str(SCHEMA_VERSION),
                "app_version": __version__,
                "world_seed": str(sim.world_seed),
                "clock": json.dumps(sim.clock.snapshot()),
                "game_config": json.dumps(sim.game_config.snapshot()),
                "scenario": json.dumps(sim.scenario.snapshot()),
            }
            conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))
            conn.executemany(
                "INSERT INTO rng_streams VALUES (?, ?)", sorted(sim.rng.snapshot().items())
            )
            conn.executemany(
                "INSERT INTO id_allocators VALUES (?, ?)", sorted(sim.ids.snapshot().items())
            )
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


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
        sim = Simulation(game_config, scenario, int(meta["world_seed"]))
        sim.clock = SimClock.from_snapshot(json.loads(meta["clock"]))
        sim.rng.restore(dict(conn.execute("SELECT name, state FROM rng_streams").fetchall()))
        sim.ids.restore(
            {str(d): int(n) for d, n in conn.execute("SELECT domain, next_id FROM id_allocators")}
        )
        return sim
    except (sqlite3.DatabaseError, MigrationError, KeyError, ValueError) as exc:
        raise SaveError(f"failed to load save {path}: {exc}") from exc
    finally:
        conn.close()
