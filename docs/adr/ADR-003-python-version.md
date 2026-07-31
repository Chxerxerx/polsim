# ADR-003: Python 3.14 primary target

Status: Accepted

## Context
The specification targets Python 3.14, permitting temporary 3.13
compatibility if a dependency lags.

## Decision
Python 3.14 is the primary and CI version. `requires-python >= 3.13` is kept
only as the specification's temporary escape hatch.

## Evidence (verified on PyPI, 2026-08-01)
NumPy 2.5.1 ships cp314 wheels; PySide6 6.11.1 supports 3.14 via stable-ABI
wheels (`requires-python <3.15,>=3.10`); zstandard, ruff, mypy, pytest,
hypothesis all support 3.14. The fallback clause is currently not needed.

## Consequences
CI runs 3.14 on Linux. The standard (GIL) build is assumed; free-threaded
builds are not a dependency of the design (the worker-thread model relies on
NumPy releasing the GIL, with a process boundary as documented fallback).
