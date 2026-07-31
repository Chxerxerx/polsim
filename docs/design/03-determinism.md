# 03 — Determinism Strategy

## Guarantee

Identical seed + identical settings + identical content versions + identical
platform and dependency versions ⇒ identical simulation results, including
after any save/load cycle. Cross-platform (Linux ↔ Windows) agreement is a
strong goal, pursued by keeping decision-path math free of BLAS-order-
dependent reductions, but the hard guarantee is per-platform.

## Rules

1. All randomness flows from named substreams derived from the world seed
   (NumPy `Generator` over Philox, keyed by seed + stream name + period),
   e.g. `worldgen.towns`, `election.turnout.2026w14`. No global `random`, no
   `numpy.random` module-level calls, no seeding from time.
2. Fixed iteration orders everywhere results depend on order: sorted stable
   IDs, never set/dict iteration order.
3. No wall-clock, locale, or filesystem-order inputs to simulation logic.
4. Ties broken by deterministic keys (stable ID), never by float equality
   chance.
5. The seed is stored in the save, displayed to the player, and shareable;
   same seed + same settings reproduces the same generated world.

## Enforcement

- Lint/CI guard rejecting `import random` and bare `np.random.*` in
  simulation packages.
- Replay harness (Milestone 1): run a scripted action sequence twice from
  the same seed and diff full world-state hashes each turn; also run with a
  save/load in the middle and diff. Every subsequent milestone adds its
  systems to this harness.
- World-state hashing utility covering the columnar store and entity tables.
