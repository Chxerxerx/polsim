# 05 — Testing Strategy

## Layers

- **Unit tests** (`tests/unit`): pure-function and single-system behavior.
- **Property tests** (Hypothesis): electoral mathematics above all — seat
  totals conserved, thresholds respected, monotonicity where the formula
  guarantees it, determinism of allocation under permuted-but-equal inputs.
- **Golden fixtures**: each electoral formula validated against published
  worked examples (e.g. known D'Hondt and Sainte-Laguë allocations).
- **Integration tests** (`tests/integration`): multi-system flows —
  campaign → polling → election → formation; scripted full election cycles.
- **Determinism/replay tests**: the Milestone-1 harness (same-seed replay
  diff, save/load-in-the-middle diff) run over every system as it lands.
- **Save/load tests**: round-trip equality of world-state hashes; migration
  tests once schema versions exist.
- **Performance benchmarks** (`tests/perf`, pytest-benchmark): the budgeted
  operations in `04-performance.md`.
- **Manual UI smoke checklist**: maintained from Milestone 9's walking-
  skeleton onward; required for milestone completion where UI is in scope.

## Completion policy

A feature or milestone is "complete" only per specification §1.3: implemented,
unit + integration tests passing, save/load and determinism tested where
applicable, performance measured where applicable, UI smoke-tested where
applicable, Linux-tested, docs and roadmap updated, no known critical defect.
Windows testing is a goal but not currently required per milestone.
