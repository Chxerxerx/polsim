# ADR-006: Development tooling

Status: Accepted (independent technical decision per specification §1.1)

## Decision
- Build: hatchling, src layout.
- Lint: ruff (E,F,W,I,N,UP,B,SIM,RUF), line length 100.
- Types: mypy --strict over `src`.
- Tests: pytest; Hypothesis for property tests; pytest-benchmark for perf.
- CI: GitHub Actions, Linux, Python 3.14 — lint, type check, tests.
- Runtime deps: NumPy, zstandard; PySide6 isolated in the optional `ui`
  extra so the simulation installs and tests headless.

## Rationale
Standard, fast, well-maintained tools satisfying the specification's strict
type checking, linting, CI, automated tests, and profiling requirements
without licensing constraints (no GPL dependencies, keeping project
licensing open).
