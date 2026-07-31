# 01 — Architecture Proposal

## Layering

```
content (data files)  →  simulation (pure Python/NumPy, headless)  →  UI (PySide6)
```

- The simulation never imports UI code and must run fully headless (tests,
  benchmarks, CI).
- The UI communicates with the simulation only through a command/snapshot
  boundary (below).
- Content is data-driven (JSON/YAML) for governments, laws, parties,
  ideologies, electoral systems, scenarios, and eras, loaded through typed
  schema validators.

## Packages

| Package | Responsibility |
|---|---|
| `core` | simulation clock, seeded RNG streams, entity IDs, config, typed message system, serialization interfaces |
| `world` | country, provinces, electoral districts, towns, world generation |
| `people` | struct-of-arrays population store, named characters, demographics, citizen memory |
| `politics` | ideology model, parties, branches, factions, organizations |
| `elections` | election law, the five electoral systems, individual voting, turnout, polling |
| `campaigns` | campaign actions, weekly schedule slots, delegation, promises |
| `government` | parliament membership, government formation, coalitions, PM selection |
| `ai` | actor goals, personalities, planning under limited information |
| `save` | SQLite hybrid store, migrations, deterministic replay support |
| `content` | bundled data-driven definitions |
| `ui` | PySide6 application, view-models, map-renderer interface |

Rules: no simulation logic in a single game-state god class; systems
reference each other by stable IDs, not direct object references, wherever
this aids saving, testing, or performance; cross-system effects flow through
the typed message system with recorded provenance (no anonymous global bus).
Every simulation outcome must be explainable from structured causes even when
hidden from the player.

## Turn pipeline (plan-then-resolve, ADR-004)

1. **Plan phase** — the player fills the weekly schedule; AI actors plan
   under identical rules and information limits.
2. **Resolve phase** (deterministic order):
   a. interactive scenes the player personally participates in (interviews,
      debates) run as resolution-time interrupts;
   b. all scheduled actions execute (player and AI identically);
   c. batch world updates (population opinion/turnout updates, media,
      polling);
   d. emergent events;
   e. end-of-turn snapshot, notifications, autosave hook.

Election weeks extend the pipeline with the full-electorate voting pass,
counting, and seat allocation.

## Simulation/UI boundary

The simulation runs on a worker thread (NumPy releases the GIL during batch
work; a process boundary is the documented fallback if profiling demands it).
The UI sends commands (schedule this action, end turn, negotiate) and
receives immutable snapshot view-models filtered through the information-
access layer, so the UI can only ever display what the player's role may
legally and practically see. The UI thread must never block > 16 ms on
simulation work.

## Map rendering

The map sits behind a small renderer interface. Initial implementation:
QGraphicsView vector polygons with choropleth map modes — sufficient for
thousands of districts. If grand-strategy scale later exceeds it, an
accelerated (OpenGL) renderer slots into the same interface (ADR-001).
