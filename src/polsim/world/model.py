"""World structure: country, provinces, electoral districts, towns (M2).

Geographic entities are lightweight relational records referenced by stable
identifiers. District seat counts are deliberately absent here: seats per
district belong to election law (specification section 11.1, Milestone 4).
The ``World`` also carries the world-specific fictional category labels and
name pools so saves are self-contained.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Province:
    province_id: int
    name: str


@dataclass(frozen=True)
class District:
    district_id: int
    name: str
    province_id: int


@dataclass(frozen=True)
class Town:
    town_id: int
    name: str
    district_id: int
    urban: bool


@dataclass
class World:
    """One generated country and its world-specific content tables."""

    country_name: str
    provinces: list[Province] = field(default_factory=list)
    districts: list[District] = field(default_factory=list)
    towns: list[Town] = field(default_factory=list)
    ethnic_groups: list[str] = field(default_factory=list)
    cultures: list[str] = field(default_factory=list)
    religions: list[str] = field(default_factory=list)  # index 0 is always "none"
    languages: list[str] = field(default_factory=list)
    given_names: list[str] = field(default_factory=list)
    family_names: list[str] = field(default_factory=list)

    def district_ids(self) -> list[int]:
        return [district.district_id for district in self.districts]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "country_name": self.country_name,
            "provinces": [asdict(province) for province in self.provinces],
            "districts": [asdict(district) for district in self.districts],
            "towns": [asdict(town) for town in self.towns],
            "ethnic_groups": self.ethnic_groups,
            "cultures": self.cultures,
            "religions": self.religions,
            "languages": self.languages,
            "given_names": self.given_names,
            "family_names": self.family_names,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> World:
        return cls(
            country_name=str(data["country_name"]),
            provinces=[Province(**province) for province in data["provinces"]],
            districts=[District(**district) for district in data["districts"]],
            towns=[Town(**town) for town in data["towns"]],
            ethnic_groups=list(data["ethnic_groups"]),
            cultures=list(data["cultures"]),
            religions=list(data["religions"]),
            languages=list(data["languages"]),
            given_names=list(data["given_names"]),
            family_names=list(data["family_names"]),
        )
