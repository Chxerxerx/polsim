# 04 — Performance Strategy and Budgets

## Approved budgets (2026-08-01)

Target hardware: 4 CPU cores, 16 GB RAM, at the default 250,000 simulated
citizens.

| Operation | Budget |
|---|---|
| Normal weekly turn | ≤ 0.5 s median, ≤ 2 s worst case |
| Election-week turn (full voting + counting + allocation) | ≤ 30 s |
| Poll generation | ≤ 200 ms per poll |
| Full save / incremental autosave | ≤ 5 s / ≤ 1 s |
| Load | ≤ 10 s |
| New-world generation | ≤ 60 s |
| UI interaction response / map-mode switch | ≤ 100 ms / ≤ 250 ms |
| Simulation blocking the UI thread | never > 16 ms |
| Memory | ≤ 2.5 GB steady state, ≤ 4 GB peak |

User amendment: the default citizen count may be adjusted (down or up) based
on measured performance; citizen count remains a game setting either way.
Any change to the 250k default requires user approval and a budget re-check.

## Strategy

- Struct-of-arrays population store with vectorized NumPy batch updates; no
  per-citizen Python objects for ordinary citizens.
- Event-driven updates with dirty-state tracking; cached demographic
  aggregates invalidated by region/attribute.
- Priority tiers: named and currently-affected citizens update in detail
  every turn; ordinary citizens update in batches and on events.
- Longer processing is acceptable (and budgeted) for elections, generation,
  and major crises; normal turns stay responsive.
- pytest-benchmark suites track the budgeted operations from Milestone 1
  onward. CI runners are not the target hardware, so CI tracks trends and
  flags regressions; acceptance against the table above is measured on a
  target-class machine.

## Hard gates

- End of Milestone 2: population storage, batch update, save, and load at
  250k within budget — before higher systems build on the store.
- End of Milestone 5: full-electorate voting pass within the election
  budget — before campaigning and election milestones build on it.
