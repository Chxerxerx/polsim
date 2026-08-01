"""Named characters layered on population rows (Milestone 3).

A character is a politically significant person: a rich record referencing
a citizen row (design doc 02). Promotion sets the citizen's population
weight to 1 — named characters always represent one person (specification
section 6.1) — and moves the surplus weight onto a neighbouring citizen in
the same district so represented population stays exactly conserved.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from polsim.people.store import PopulationStore


@dataclass
class Character:
    character_id: int
    row: int  # citizen row index; citizen id = row + 1
    full_name: str
    charisma: float  # 0..1
    competence: float  # 0..1
    integrity: float  # 0..1

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Character:
        return cls(
            character_id=int(data["character_id"]),
            row=int(data["row"]),
            full_name=str(data["full_name"]),
            charisma=float(data["charisma"]),
            competence=float(data["competence"]),
            integrity=float(data["integrity"]),
        )


class CharacterRegistry:
    """All named characters, indexed by id and by citizen row."""

    def __init__(self) -> None:
        self._by_id: dict[int, Character] = {}
        self._by_row: dict[int, int] = {}

    def add(self, character: Character) -> None:
        if character.character_id in self._by_id:
            raise ValueError(f"duplicate character id {character.character_id}")
        if character.row in self._by_row:
            raise ValueError(f"row {character.row} is already a character")
        self._by_id[character.character_id] = character
        self._by_row[character.row] = character.character_id

    def get(self, character_id: int) -> Character:
        return self._by_id[character_id]

    def by_row(self, row: int) -> Character | None:
        character_id = self._by_row.get(row)
        return None if character_id is None else self._by_id[character_id]

    def all_ids(self) -> list[int]:
        return sorted(self._by_id)

    def __len__(self) -> int:
        return len(self._by_id)

    def to_json_list(self) -> list[dict[str, Any]]:
        return [self._by_id[cid].to_json_dict() for cid in sorted(self._by_id)]

    @classmethod
    def from_json_list(cls, data: list[dict[str, Any]]) -> CharacterRegistry:
        registry = cls()
        for entry in data:
            registry.add(Character.from_json_dict(entry))
        return registry


def set_weight_one(store: PopulationStore, row: int) -> None:
    """Reduce a promoted citizen's weight to 1, conserving district totals.

    The surplus weight moves to the nearest same-district row that is not
    itself weight 1 already (deterministic scan).
    """
    weights = store.column("population_weight")
    surplus = int(weights[row]) - 1
    if surplus <= 0:
        return
    district = int(store.column("district")[row])
    start, length = store.district_range(district)
    recipient = -1
    for offset in range(1, length):
        for candidate in (row + offset, row - offset):
            if start <= candidate < start + length and candidate != row:
                recipient = candidate
                break
        if recipient != -1:
            break
    if recipient == -1:
        raise ValueError(f"no recipient row for surplus weight in district {district}")
    district_weights = store.district_column(district, "population_weight").copy()
    district_weights[row - start] = 1
    district_weights[recipient - start] += surplus
    store.set_district_values(district, "population_weight", district_weights)
