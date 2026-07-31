# ADR-002: Save storage — SQLite hybrid

Status: Accepted (decision delegated to the architect per specification §31)

## Context
Saves must handle 250k-citizen state, fast incremental autosaves, schema
migrations, mod content, corruption detection, interrupted-save recovery,
and deterministic replay. Options: pure relational SQLite, custom structured
binary (+zstd), hybrid.

## Decision
A single SQLite file per save, WAL mode, used as a container:
- relational tables for entities, relations, laws, offices, history, and the
  global event log;
- population columns stored as zstd-compressed NumPy chunk blobs partitioned
  by district, with dirty-chunk tracking for ≤1 s incremental autosaves;
- `schema_version` table + stepwise migration framework;
- world seed and player/AI action log retained for deterministic replay;
- per-chunk checksums plus SQLite integrity checking; WAL provides
  interrupted-write recovery.

## Rationale
Row-per-citizen SQLite is too slow for bulk state; pure custom binary means
hand-rolling transactions, recovery, and migrations that SQLite provides.
The hybrid keeps single-file convenience, crash safety, queryability for
debugging, and bulk-column speed.

## Consequences
`polsim.save` owns all persistence; systems expose column snapshots and
entity serializers through `core` interfaces. Save format is versioned from
the first milestone.
