from __future__ import annotations

import sqlite3

import pytest

from polsim.save.migrations import MigrationError, apply_migrations


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def test_stepwise_order() -> None:
    calls: list[int] = []
    registry = {1: lambda c: calls.append(1), 2: lambda c: calls.append(2)}
    result = apply_migrations(_conn(), 1, target_version=3, registry=registry)
    assert result == 3
    assert calls == [1, 2]


def test_already_current_is_noop() -> None:
    assert apply_migrations(_conn(), 1, target_version=1, registry={}) == 1


def test_gap_in_registry_raises() -> None:
    registry = {1: lambda c: None}  # nothing registered from version 2
    with pytest.raises(MigrationError):
        apply_migrations(_conn(), 1, target_version=3, registry=registry)


def test_downgrade_raises() -> None:
    with pytest.raises(MigrationError):
        apply_migrations(_conn(), 5, target_version=1, registry={})
