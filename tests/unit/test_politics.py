"""Political system generation and operations (Milestone 3)."""

from __future__ import annotations

import numpy as np
import pytest
from tests.conftest import small_sim

from polsim.politics.labels import axis_ids, classify_axes
from polsim.politics.model import BranchLevel, LeadershipSelection
from polsim.politics.registry import FactionConflictError

SCALE = float(np.sqrt(len(axis_ids())))


def _party_vector(sim: object, party_id: int) -> np.ndarray:
    party = sim.politics.parties[party_id]  # type: ignore[attr-defined]
    return np.asarray([party.axes[axis] for axis in axis_ids()])


def test_parties_are_ideologically_distinct() -> None:
    sim = small_sim()
    party_ids = sorted(sim.politics.parties)
    assert len(party_ids) == 6
    for index, first in enumerate(party_ids):
        for second in party_ids[index + 1 :]:
            distance = float(
                np.linalg.norm(_party_vector(sim, first) - _party_vector(sim, second)) / SCALE
            )
            assert distance > 0.12


def test_membership_is_ideologically_compatible() -> None:
    sim = small_sim()
    store = sim.population
    axes = np.stack(
        [store.column(f"axis_{axis}").astype(np.float64) for axis in axis_ids()], axis=1
    )
    members = store.column("party_member")
    preferred = store.column("preferred_party")
    share = float((members > 0).mean())
    assert 0.005 <= share <= 0.08
    vectors = {party_id: _party_vector(sim, party_id) for party_id in sim.politics.parties}

    def distance_to(rows: np.ndarray, party_of_row: np.ndarray) -> float:
        distances = [
            float(np.linalg.norm(axes[row] - vectors[int(party_of_row[row])]) / SCALE)
            for row in rows.tolist()
        ]
        return float(np.mean(distances))

    member_rows = np.flatnonzero(members > 0)
    adult_rows = np.flatnonzero(
        (preferred > 0) & (-store.column("birth_week") >= 18 * 52)
    )
    # Aggregate: members are closer to their party than adults are to their
    # preferred party in general (per-party means are noise at test scale).
    assert distance_to(member_rows, members) < distance_to(adult_rows, preferred)
    # Per-party check only where the sample is statistically meaningful.
    for party_id in sorted(sim.politics.parties):
        rows = np.flatnonzero(members == party_id)
        if len(rows) < 15:
            continue
        member_distance = np.linalg.norm(axes[rows] - vectors[party_id], axis=1).mean() / SCALE
        all_distance = np.linalg.norm(axes - vectors[party_id], axis=1).mean() / SCALE
        assert member_distance < all_distance


def test_leaders_are_weight_one_characters() -> None:
    sim = small_sim()
    weights = sim.population.column("population_weight")
    for party in sim.politics.parties.values():
        assert party.leader_id is not None
        leader = sim.characters.get(party.leader_id)
        assert int(weights[leader.row]) == 1
        assert leader.full_name
    for character_id in sim.characters.all_ids():
        assert int(weights[sim.characters.get(character_id).row]) == 1
    assert int(weights.sum()) == sim.scenario.represented_population


def test_branches_partition_membership() -> None:
    sim = small_sim()
    members = sim.population.column("party_member")
    for party_id in sorted(sim.politics.parties):
        branches = sim.politics.party_branches(party_id)
        levels = {branch.level for branch in branches}
        assert BranchLevel.NATIONAL in levels
        total = int((members == party_id).sum())
        district_total = sum(
            branch.member_count for branch in branches if branch.level is BranchLevel.DISTRICT
        )
        assert district_total == total


def test_faction_members_are_aligned_and_contradictions_rejected() -> None:
    sim = small_sim()
    registry = sim.politics
    store = sim.population
    by_name = {faction.name: faction for faction in registry.factions.values()}
    devout = by_name["Devout Assembly"]
    secular = by_name["Secular Network"]
    assert devout.member_ids and secular.member_ids
    for faction in registry.factions.values():
        for character_id in faction.member_ids:
            row = sim.characters.get(character_id).row
            for issue, stance in faction.stances.items():
                assert float(store.column(f"issue_{issue}")[row]) * stance > 0.35
    devout_member = devout.member_ids[0]
    assert not registry.can_join_faction(devout_member, secular.faction_id)
    with pytest.raises(FactionConflictError):
        registry.join_faction(devout_member, secular.faction_id)


def test_cross_party_faction_exists() -> None:
    sim = small_sim()
    members = sim.population.column("party_member")
    preferred = sim.population.column("preferred_party")
    for faction in sim.politics.factions.values():
        parties = set()
        for character_id in faction.member_ids:
            row = sim.characters.get(character_id).row
            party = int(members[row]) or int(preferred[row])
            if party:
                parties.add(party)
        if len(parties) >= 2:
            return
    pytest.fail("no faction spans multiple parties")


def test_organizations_and_membership_column_agree() -> None:
    sim = small_sim()
    column = sim.population.column("primary_organization")
    valid = set(sim.politics.organizations) | {0}
    assert set(np.unique(column).tolist()) <= valid
    for organization in sim.politics.organizations.values():
        assert organization.member_count == int(
            (column == organization.organization_id).sum()
        )


def test_endorsements_are_ideologically_sensible() -> None:
    sim = small_sim()
    registry = sim.politics
    assert registry.endorsements
    ids = axis_ids()
    for endorsement in registry.endorsements:
        organization = registry.organizations[endorsement.organization_id]
        vector = np.asarray([organization.axes.get(axis, 0.0) for axis in ids])
        relevant = np.asarray([1.0 if axis in organization.axes else 0.0 for axis in ids])
        distances = {
            party_id: float(
                np.sqrt((((_party_vector(sim, party_id) - vector) ** 2) * relevant).sum())
            )
            for party_id in sorted(registry.parties)
        }
        endorsed = distances[endorsement.party_id]
        assert endorsed <= min(distances.values()) + 1e-9


@pytest.mark.parametrize("rule", list(LeadershipSelection))
def test_leadership_election_is_deterministic_per_rule(rule: LeadershipSelection) -> None:
    winners = []
    for _ in range(2):
        sim = small_sim()
        party_id = sorted(sim.politics.parties)[0]
        sim.politics.parties[party_id].rules.leadership_selection = rule
        winner = sim.politics.elect_leader(
            party_id, sim.population, sim.characters, sim.rng.stream("test.election")
        )
        assert winner in sim.politics.party_characters(party_id)
        assert sim.politics.parties[party_id].leader_id == winner
        winners.append(winner)
    assert winners[0] == winners[1]


def test_citizen_labels_are_diverse_and_disagree_within_label() -> None:
    sim = small_sim()
    store = sim.population
    axes = np.stack(
        [store.column(f"axis_{axis}").astype(np.float64) for axis in axis_ids()], axis=1
    )
    labels = np.asarray(classify_axes(axes))
    assert len(set(labels.tolist())) >= 4
    largest = max(set(labels.tolist()), key=lambda value: int((labels == value).sum()))
    group = labels == largest
    spread = float(store.column("issue_progressive_taxation")[group].std())
    assert spread > 0.1  # same label, real disagreement on individual issues
