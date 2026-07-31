# Roadmap (living document — source of truth for milestone status)

Last updated: 2026-08-01 (session: Milestone 1 delivery).

## Decision log

| Date | Decision | Record |
|---|---|---|
| 2026-08-01 | GUI framework: PySide6 + map-renderer abstraction | ADR-001 (user-approved) |
| 2026-08-01 | Performance budgets approved; citizen count adjustable on measured performance with user approval | docs/design/04 |
| 2026-08-01 | Default scenario: 10M represented / 200 seats / list-PR D'Hondt 4% | ADR-005 (user-approved) |
| 2026-08-01 | Turn model: plan-then-resolve with interactive interrupts | ADR-004 (user-approved) |
| 2026-08-01 | Save storage: SQLite hybrid | ADR-002 (delegated per spec §31) |
| 2026-08-01 | Repository: GitHub; pull at session start, zip/patch handoff back | this file |
| 2026-08-01 | Repository URL: https://github.com/Chxerxerx/polsim | this file |

## Open items (non-blocking)

- Final game name (`polsim` is a placeholder).
- Project license (dependencies avoid GPL so all options stay open).

## Milestone status

Completion for every milestone follows specification §1.3 (tests, save/load
and determinism where applicable, measured performance where applicable,
Linux-tested, docs + this roadmap updated, no known critical defects).

| Milestone | Scope (specification §34) | Status |
|---|---|---|
| M0 | Architecture & technical decisions: design docs, ADRs, data model, determinism/performance/testing strategies, package scaffold, CI, this roadmap | **Complete** (2026-08-01). Note: the initial GitHub web upload dropped hidden files (.gitignore, CI workflow) and added __pycache__; repaired in a housekeeping commit. CI activates on the first `git push`. |
| M1 | Core foundation: weekly clock, deterministic RNG streams, entity IDs, game/scenario config, seed generation, basic save/load, logging, test + profiling infrastructure, replay harness | **Delivered for review** (2026-08-01): all M1 systems implemented; 61 tests passing incl. replay harness (same-seed and save/load-mid-run hash equality) and save round-trips; randomness guard test active; ruff + mypy --strict clean; verified on Linux/CPython 3.14.4. M1 baselines (sandbox hardware): advance_week ~1 µs, state_hash ~70 µs, save ~5.5 ms, load ~0.5 ms. Complete when pushed and CI is green. |
| M2 | Geography & population: country/provinces/districts/towns, generation, SoA store, weights, demographics, aggregates, event-driven updates. **Hard gate: 250k storage/update/save/load within budget** | Not started |
| M2.5 | UI walking skeleton (post-ADR-001): PySide6 shell, worker-thread boundary, map spike, one live view-model | Not started |
| M3 | Ideology, parties, factions, organizations | Not started |
| M4 | Electoral-law framework: five systems, deterministic allocation, golden-fixture + property tests | Not started |
| M5 | Citizen voting & polling. **Hard gate: full-electorate voting pass within election budget** | Not started |
| M6 | Campaigning: all initial actions, schedule slots, delegation, resources, skills, backfire, promise tracking | Not started |
| M7 | Election & parliament: scheduling, election day, counting, allocation, results, recounts, membership, history | Not started |
| M8 | Government formation: coalitions, agreements, minority/caretaker, PM selection, confidence, collapse, snap elections | Not started |
| M9 | MVP UI: all views on the walking skeleton (dashboard, map, party, candidate, polling, schedule, election, parliament, negotiation, notifications, save/load) | Not started |
| M10 | MVP validation & optimization: acceptance scenario (spec §35), determinism + save/load + repeated elections, profiling, Linux packaging notes, manual UI smoke | Not started |

## Later (post-MVP, ordered per specification)

Legislature depth, ministries, civil service, judiciary, rights, economy,
media depth, corruption & political crime, historical eras, real countries,
procedural countries, additional government systems, international politics,
trade, military strategy, war, revolutions, civil wars, modding. Grand-
strategy military control remains late.

## Session protocol

Per specification §1.2: at each session start, pull the repository, read this
roadmap, inspect the systems being changed and their tests; the repository —
not conversational memory — is the source of truth.
