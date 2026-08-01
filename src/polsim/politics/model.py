"""Political entity records: parties, branches, factions, organizations,
endorsements (Milestone 3).

Records reference people by character id or citizen row and each other by
stable ids; membership of ordinary citizens lives in population columns
(``preferred_party``, ``party_member``, ``primary_organization``). Entity
attributes here are the Milestone 3 subset; funding, reputation, scandals,
and campaign resources arrive with their systems (M6+).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class LeadershipSelection(Enum):
    ALL_MEMBERS = "all_members"
    DELEGATES = "delegates"
    EXECUTIVE = "executive"


class BranchLevel(Enum):
    NATIONAL = "national"
    PROVINCE = "province"
    DISTRICT = "district"


class FactionCategory(Enum):
    IDEOLOGICAL = "ideological"
    REGIONAL = "regional"
    RELIGIOUS = "religious"
    SINGLE_ISSUE = "single_issue"


class OrganizationKind(Enum):
    LABOR_UNION = "labor_union"
    EMPLOYER_ASSOCIATION = "employer_association"
    AGRARIAN_ASSOCIATION = "agrarian_association"
    RELIGIOUS = "religious"
    ADVOCACY = "advocacy"
    PROFESSIONAL = "professional"
    VETERANS = "veterans"


@dataclass
class PartyRules:
    leadership_selection: LeadershipSelection
    membership_open: bool
    discipline: float  # 0..1

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "leadership_selection": self.leadership_selection.value,
            "membership_open": self.membership_open,
            "discipline": self.discipline,
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> PartyRules:
        return cls(
            leadership_selection=LeadershipSelection(data["leadership_selection"]),
            membership_open=bool(data["membership_open"]),
            discipline=float(data["discipline"]),
        )


@dataclass
class Party:
    party_id: int
    name: str
    abbreviation: str
    label_id: str  # derived at creation; recomputable from axes
    axes: dict[str, float]
    issues: dict[str, float]
    rules: PartyRules
    founded_week: int
    leader_id: int | None = None
    deputy_id: int | None = None

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rules"] = self.rules.to_json_dict()
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Party:
        return cls(
            party_id=int(data["party_id"]),
            name=str(data["name"]),
            abbreviation=str(data["abbreviation"]),
            label_id=str(data["label_id"]),
            axes={str(k): float(v) for k, v in data["axes"].items()},
            issues={str(k): float(v) for k, v in data["issues"].items()},
            rules=PartyRules.from_json_dict(data["rules"]),
            founded_week=int(data["founded_week"]),
            leader_id=None if data["leader_id"] is None else int(data["leader_id"]),
            deputy_id=None if data["deputy_id"] is None else int(data["deputy_id"]),
        )


@dataclass
class Branch:
    branch_id: int
    party_id: int
    level: BranchLevel
    region_id: int  # 0 for national, else province or district id
    chair_id: int | None
    member_count: int

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Branch:
        return cls(
            branch_id=int(data["branch_id"]),
            party_id=int(data["party_id"]),
            level=BranchLevel(data["level"]),
            region_id=int(data["region_id"]),
            chair_id=None if data["chair_id"] is None else int(data["chair_id"]),
            member_count=int(data["member_count"]),
        )


@dataclass
class Faction:
    faction_id: int
    name: str
    category: FactionCategory
    stances: dict[str, int]  # issue id -> -1 or +1 (defining commitments)
    member_ids: list[int] = field(default_factory=list)  # character ids

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Faction:
        return cls(
            faction_id=int(data["faction_id"]),
            name=str(data["name"]),
            category=FactionCategory(data["category"]),
            stances={str(k): int(v) for k, v in data["stances"].items()},
            member_ids=[int(v) for v in data["member_ids"]],
        )


@dataclass
class Organization:
    organization_id: int
    name: str
    kind: OrganizationKind
    axes: dict[str, float]
    leader_id: int | None
    member_count: int

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Organization:
        return cls(
            organization_id=int(data["organization_id"]),
            name=str(data["name"]),
            kind=OrganizationKind(data["kind"]),
            axes={str(k): float(v) for k, v in data["axes"].items()},
            leader_id=None if data["leader_id"] is None else int(data["leader_id"]),
            member_count=int(data["member_count"]),
        )


@dataclass
class Endorsement:
    organization_id: int
    party_id: int
    strength: float  # 0..1
    since_week: int

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> Endorsement:
        return cls(
            organization_id=int(data["organization_id"]),
            party_id=int(data["party_id"]),
            strength=float(data["strength"]),
            since_week=int(data["since_week"]),
        )
