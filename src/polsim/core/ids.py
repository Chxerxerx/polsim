"""Stable entity identifiers (Milestone 1).

Every entity domain uses 64-bit integer identifiers wrapped in ``NewType``
for type safety under strict mypy. Identifiers are allocated monotonically,
are permanent across save/load, and are never reused within a world
(design doc 02).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NewType

CitizenId = NewType("CitizenId", int)
CharacterId = NewType("CharacterId", int)
PartyId = NewType("PartyId", int)
FactionId = NewType("FactionId", int)
OrganizationId = NewType("OrganizationId", int)
ProvinceId = NewType("ProvinceId", int)
DistrictId = NewType("DistrictId", int)
TownId = NewType("TownId", int)
EventId = NewType("EventId", int)
LawId = NewType("LawId", int)

KNOWN_DOMAINS: tuple[str, ...] = (
    "citizen",
    "character",
    "party",
    "faction",
    "organization",
    "province",
    "district",
    "town",
    "event",
    "law",
)


class IdRegistry:
    """Monotonic per-domain identifier allocation with snapshot/restore."""

    def __init__(self) -> None:
        self._next: dict[str, int] = dict.fromkeys(KNOWN_DOMAINS, 1)

    def allocate(self, domain: str) -> int:
        if domain not in self._next:
            raise ValueError(f"unknown id domain: {domain!r}")
        allocated = self._next[domain]
        self._next[domain] = allocated + 1
        return allocated

    def snapshot(self) -> dict[str, int]:
        return dict(self._next)

    def restore(self, data: Mapping[str, int]) -> None:
        for domain, next_id in data.items():
            if domain not in self._next:
                raise ValueError(f"unknown id domain in save: {domain!r}")
            if next_id < 1:
                raise ValueError(f"invalid allocator value for {domain!r}: {next_id}")
        self._next.update(data)
