"""Save-schema migration framework (Milestone 1, ADR-002).

Migrations are functions keyed by the schema version they upgrade *from*;
:func:`apply_migrations` runs them stepwise. Schema version 1 is the
baseline, so the registry is empty today; the framework and its ordering
behavior are tested now so later versions slot in safely.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping

SCHEMA_VERSION = 2

Migration = Callable[[sqlite3.Connection], None]

def _reject_pre_world_save(conn: sqlite3.Connection) -> None:
    """Schema 1 was the internal Milestone-1 format with no world data.

    A world cannot be synthesized retroactively, and no compatibility was
    promised for pre-playable internal schemas; compatibility guarantees
    begin with the first playable release.
    """
    raise MigrationError(
        "this save predates world generation (internal schema 1) and cannot "
        "be upgraded; start a new game"
    )


MIGRATIONS: dict[int, Migration] = {1: _reject_pre_world_save}


class MigrationError(RuntimeError):
    """Raised when a save cannot be migrated to the current schema."""


def apply_migrations(
    conn: sqlite3.Connection,
    from_version: int,
    *,
    target_version: int = SCHEMA_VERSION,
    registry: Mapping[int, Migration] | None = None,
) -> int:
    """Upgrade stepwise from ``from_version`` to ``target_version``.

    Returns the resulting version. Raises :class:`MigrationError` if the
    save is newer than this build or the registry has a gap.
    """
    if from_version > target_version:
        raise MigrationError(
            f"save schema {from_version} is newer than supported version {target_version}"
        )
    active = MIGRATIONS if registry is None else registry
    version = from_version
    while version < target_version:
        migration = active.get(version)
        if migration is None:
            raise MigrationError(f"no migration registered from schema version {version}")
        migration(conn)
        version += 1
    return version
