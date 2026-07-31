# 06 — Identified Risks

| # | Risk | Severity | Mitigation | Status |
|---|---|---|---|---|
| 1 | 250k-citizen performance (naive objects unusable) | Critical | SoA columnar store, vectorization, tiers, dirty flags; hard gate at M2 | Design adopted |
| 2 | Citizen memory blowing up memory/save size | High | Global event log + fixed-width (event, salience) pairs with decay; gate at M2 | Design adopted |
| 3 | Determinism regressions (hidden global RNG, iteration order) | High | Named substreams, lint guard, replay harness from M1 | Planned M1 |
| 4 | Cross-platform float divergence (Linux/Windows) | Medium | Per-platform guarantee; avoid BLAS-order-dependent reductions in decision paths | Accepted, monitored |
| 5 | UI freezes during long turns | High | Worker-thread simulation, command/snapshot boundary, 16 ms rule; process fallback documented | Design adopted |
| 6 | Big-bang UI risk at M9 | Medium | Walking-skeleton UI inserted ~M2–M3 after framework approval | Approved |
| 7 | Save performance / corruption at scale | Medium | SQLite WAL + compressed dirty chunks + checksums (ADR-002) | Design adopted |
| 8 | Scope creep from the very large specification | High | MVP non-goals list, milestone exit criteria, interfaces-not-implementations for deferred systems | Ongoing |
| 9 | Dependency readiness for Python 3.14 | Low | Verified 2026-08-01: NumPy 2.5.1 (cp314), PySide6 6.11.1 (abi3, <3.15) | Resolved |
