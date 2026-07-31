# polsim (working title)

A turn-based political simulation and (eventually) grand-strategy game in Python.
Primary inspirations: Lawgivers II, Democracy 4, Victoria 3.

**Status: Milestone 0 — architecture and technical decisions. No playable content yet.**

The MVP target is a complete national election cycle in a fictional modern
parliamentary republic with ~250,000 persistent, individually simulated,
weighted citizens: party selection/creation, weekly campaign scheduling with
delegation, polling with uncertainty, individual citizen voting, seat
allocation under configurable election law, coalition negotiation, and
continued play in government or opposition.

## Documentation

- `docs/ROADMAP.md` — living roadmap and milestone status (source of truth)
- `docs/design/` — design documents (scope, architecture, data model,
  determinism, performance, testing, risks)
- `docs/adr/` — architecture decision records

## Development setup

Requires Python 3.14 (3.13 temporarily acceptable; see ADR-003).

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'          # simulation + dev tools (headless)
pip install -e '.[dev,ui]'       # additionally installs PySide6
ruff check . && mypy src && pytest
```

The simulation must always run and test headless; the UI extra is only
needed for interface work.

## Open items (non-blocking)

- Final game name (`polsim` is a placeholder package name).
- Project license (no license file yet; dependencies deliberately avoid GPL
  so both open-source and proprietary licensing remain possible).
