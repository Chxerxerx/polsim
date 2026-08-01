"""Political registry: entity storage, faction constraints, party elections
(Milestone 3).

Faction joining enforces the contradiction rule from specification
section 9: a character may hold multiple compatible memberships but never
two factions with opposite defining stances on the same issue.

Internal leadership elections implement specification section 8.2 at
Milestone-3 depth: the electorate is defined by party rules, member votes
are population-weighted, and electors prefer the ideologically nearest
candidate with a small charisma effect.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from polsim.people.characters import CharacterRegistry
from polsim.people.store import PopulationStore
from polsim.politics.labels import axis_ids
from polsim.politics.model import (
    Branch,
    BranchLevel,
    Endorsement,
    Faction,
    LeadershipSelection,
    Organization,
    Party,
)


class FactionConflictError(ValueError):
    """Joining would combine directly contradictory factions."""


class PoliticalRegistry:
    """Parties, branches, factions, organizations, endorsements."""

    def __init__(self) -> None:
        self.parties: dict[int, Party] = {}
        self.branches: dict[int, Branch] = {}
        self.factions: dict[int, Faction] = {}
        self.organizations: dict[int, Organization] = {}
        self.endorsements: list[Endorsement] = []

    # -- factions -----------------------------------------------------------

    def factions_of(self, character_id: int) -> list[Faction]:
        return [
            faction
            for faction in self.factions.values()
            if character_id in faction.member_ids
        ]

    def can_join_faction(self, character_id: int, faction_id: int) -> bool:
        target = self.factions[faction_id]
        for held in self.factions_of(character_id):
            for issue, stance in target.stances.items():
                if held.stances.get(issue, stance) != stance:
                    return False
        return True

    def join_faction(self, character_id: int, faction_id: int) -> None:
        if not self.can_join_faction(character_id, faction_id):
            raise FactionConflictError(
                f"character {character_id} holds a faction with a contradictory stance"
            )
        members = self.factions[faction_id].member_ids
        if character_id not in members:
            members.append(character_id)

    # -- party structure ----------------------------------------------------

    def party_branches(self, party_id: int) -> list[Branch]:
        return sorted(
            (b for b in self.branches.values() if b.party_id == party_id),
            key=lambda branch: branch.branch_id,
        )

    def party_characters(self, party_id: int) -> list[int]:
        seen: set[int] = set()
        party = self.parties[party_id]
        for candidate in (party.leader_id, party.deputy_id):
            if candidate is not None:
                seen.add(candidate)
        for branch in self.party_branches(party_id):
            if branch.chair_id is not None:
                seen.add(branch.chair_id)
        return sorted(seen)

    # -- internal leadership elections (spec 8.2, M3 depth) -----------------

    def elect_leader(
        self,
        party_id: int,
        store: PopulationStore,
        characters: CharacterRegistry,
        rng: np.random.Generator,
    ) -> int:
        """Run the party's leadership election; returns the winning character id."""
        party = self.parties[party_id]
        candidate_ids = self.party_characters(party_id)
        if not candidate_ids:
            raise ValueError(f"party {party_id} has no eligible candidates")
        axes = np.stack(
            [
                np.asarray(
                    [
                        float(store.column(f"axis_{axis}")[characters.get(cid).row])
                        for axis in axis_ids()
                    ]
                )
                for cid in candidate_ids
            ]
        )
        charisma = np.asarray([characters.get(cid).charisma for cid in candidate_ids])

        rule = party.rules.leadership_selection
        if rule is LeadershipSelection.ALL_MEMBERS:
            member_rows = np.flatnonzero(store.column("party_member") == party_id)
            elector_axes = np.stack(
                [store.column(f"axis_{axis}")[member_rows] for axis in axis_ids()], axis=1
            )
            elector_weights = store.column("population_weight")[member_rows].astype(np.float64)
        else:
            if rule is LeadershipSelection.DELEGATES:
                elector_ids = [
                    branch.chair_id
                    for branch in self.party_branches(party_id)
                    if branch.chair_id is not None
                ]
            else:  # EXECUTIVE
                elector_ids = [
                    branch.chair_id
                    for branch in self.party_branches(party_id)
                    if branch.chair_id is not None and branch.level is not BranchLevel.DISTRICT
                ]
                for extra in (party.leader_id, party.deputy_id):
                    if extra is not None:
                        elector_ids.append(extra)
            elector_ids = sorted(set(elector_ids)) or candidate_ids
            rows = [characters.get(cid).row for cid in elector_ids]
            elector_axes = np.stack(
                [store.column(f"axis_{axis}")[rows] for axis in axis_ids()], axis=1
            )
            elector_weights = np.ones(len(rows))

        distances = np.linalg.norm(elector_axes[:, None, :] - axes[None, :, :], axis=2)
        appeal = -distances + 0.25 * charisma[None, :]
        appeal = appeal + rng.normal(0.0, 0.02, size=appeal.shape)
        votes = np.bincount(
            np.argmax(appeal, axis=1), weights=elector_weights, minlength=len(candidate_ids)
        )
        winner_index = int(np.argmax(votes))  # ties: lowest candidate id (sorted order)
        winner = candidate_ids[winner_index]
        party.leader_id = winner
        return winner

    # -- serialization ------------------------------------------------------

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "parties": [self.parties[pid].to_json_dict() for pid in sorted(self.parties)],
            "branches": [self.branches[bid].to_json_dict() for bid in sorted(self.branches)],
            "factions": [self.factions[fid].to_json_dict() for fid in sorted(self.factions)],
            "organizations": [
                self.organizations[oid].to_json_dict() for oid in sorted(self.organizations)
            ],
            "endorsements": [entry.to_json_dict() for entry in self.endorsements],
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> PoliticalRegistry:
        registry = cls()
        for entry in data["parties"]:
            party = Party.from_json_dict(entry)
            registry.parties[party.party_id] = party
        for entry in data["branches"]:
            branch = Branch.from_json_dict(entry)
            registry.branches[branch.branch_id] = branch
        for entry in data["factions"]:
            faction = Faction.from_json_dict(entry)
            registry.factions[faction.faction_id] = faction
        for entry in data["organizations"]:
            organization = Organization.from_json_dict(entry)
            registry.organizations[organization.organization_id] = organization
        registry.endorsements = [
            Endorsement.from_json_dict(entry) for entry in data["endorsements"]
        ]
        return registry

    def canonical_json(self) -> str:
        return json.dumps(self.to_json_dict(), sort_keys=True, separators=(",", ":"))
