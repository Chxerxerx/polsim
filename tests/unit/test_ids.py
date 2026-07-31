from __future__ import annotations

import pytest

from polsim.core.ids import KNOWN_DOMAINS, IdRegistry


def test_monotonic_and_independent_domains() -> None:
    ids = IdRegistry()
    assert [ids.allocate("citizen") for _ in range(3)] == [1, 2, 3]
    assert ids.allocate("party") == 1  # domains do not share counters


def test_unknown_domain_rejected() -> None:
    ids = IdRegistry()
    with pytest.raises(ValueError):
        ids.allocate("dragon")


def test_snapshot_restore_never_reuses() -> None:
    ids = IdRegistry()
    for _ in range(5):
        ids.allocate("event")
    restored = IdRegistry()
    restored.restore(ids.snapshot())
    assert restored.allocate("event") == 6


def test_restore_validates() -> None:
    ids = IdRegistry()
    with pytest.raises(ValueError):
        ids.restore({"dragon": 1})
    with pytest.raises(ValueError):
        ids.restore({"citizen": 0})


def test_all_known_domains_start_at_one() -> None:
    ids = IdRegistry()
    assert all(ids.allocate(domain) == 1 for domain in KNOWN_DOMAINS)
