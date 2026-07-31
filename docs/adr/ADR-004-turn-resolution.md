# ADR-004: Turn resolution — plan-then-resolve with interactive interrupts

Status: Accepted (user-approved 2026-08-01)

## Context
Turns are weekly with schedule slots. Interviews and debates are interactive
multi-round scenes (specification §12.1). Options: (a) simultaneous
plan-then-resolve with resolution-time interrupts for scenes the player
personally participates in; (b) fully sequential interactive weeks.

## Decision
Option (a). The player plans the week and ends the turn; all actors resolve
simultaneously under identical rules; resolution pauses for the player's own
interactive scenes.

## Rationale
Fair to AI actors under the same-rules requirement, parallelizes and
vectorizes cleanly, and keeps the turn pipeline deterministic and testable
(interactive inputs enter as recorded actions in the replay log).

## Consequences
The `core` turn pipeline is phase-ordered (plan → interrupts → actions →
batch world updates → events → snapshot/autosave). Interactive scene inputs
are serialized into the action log for deterministic replay.
