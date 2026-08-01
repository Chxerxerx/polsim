"""Political entity generation (Milestone 3).

Generates the initial party system, party membership and preference for
every citizen, named characters (leaders, deputies, branch chairs, and
organization leaders — all set to population weight 1 with exact
conservation), local branches at national/province/district level, factions
including cross-party factions, organizations, and initial endorsements.
All draws come from the ``worldgen.politics`` stream.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from polsim.content.loader import load_ideology_labels
from polsim.core.ids import IdRegistry
from polsim.people.characters import Character, CharacterRegistry, set_weight_one
from polsim.people.store import PopulationStore
from polsim.politics.ideology import citizen_axis_matrix, fill_political_columns
from polsim.politics.labels import axis_ids, classify_axes
from polsim.politics.model import (
    Branch,
    BranchLevel,
    Endorsement,
    Faction,
    FactionCategory,
    LeadershipSelection,
    Organization,
    OrganizationKind,
    Party,
    PartyRules,
)
from polsim.politics.registry import PoliticalRegistry
from polsim.world.model import World

Array = NDArray[Any]

DEFAULT_PARTY_LABELS = (
    "social_democrat",
    "conservative",
    "liberal",
    "green",
    "nationalist",
    "socialist",
)


def generate_politics(
    world: World,
    store: PopulationStore,
    ids: IdRegistry,
    characters: CharacterRegistry,
    rng: np.random.Generator,
) -> PoliticalRegistry:
    registry = PoliticalRegistry()
    fill_political_columns(store, world, rng)
    _generate_parties(registry, ids, rng)
    _assign_citizen_party_columns(registry, store, rng)
    _generate_characters_and_branches(registry, world, store, ids, characters, rng)
    _generate_organizations(registry, world, store, ids, characters, rng)
    _generate_factions(registry, store, ids, characters)
    _generate_endorsements(registry, rng)
    return registry


# -- parties ----------------------------------------------------------------


def _generate_parties(
    registry: PoliticalRegistry, ids: IdRegistry, rng: np.random.Generator
) -> None:
    labels = {label.label_id: label for label in load_ideology_labels()}
    for label_id in DEFAULT_PARTY_LABELS:
        label = labels[label_id]
        axes = {
            axis: float(np.clip(label.axes.get(axis, 0.0) + rng.normal(0.0, 0.10), -1.0, 1.0))
            for axis in axis_ids()
        }
        name = label.party_names[int(rng.integers(0, len(label.party_names)))]
        abbreviation = "".join(word[0] for word in name.split() if word[0].isupper())[:4]
        rules = PartyRules(
            leadership_selection=list(LeadershipSelection)[int(rng.integers(0, 3))],
            membership_open=bool(rng.random() < 0.8),
            discipline=float(rng.uniform(0.4, 0.9)),
        )
        party = Party(
            party_id=ids.allocate("party"),
            name=name,
            abbreviation=abbreviation or name[:3].upper(),
            label_id=classify_axes(
                np.asarray([[axes[axis] for axis in axis_ids()]])
            )[0],
            axes=axes,
            issues={},
            rules=rules,
            founded_week=0,
        )
        # Party issue positions derive from party axes via the same loadings.
        from polsim.content.loader import load_issues

        for issue in load_issues():
            total = sum(abs(weight) for weight in issue.axis_weights.values())
            value = sum(
                weight * axes[axis] for axis, weight in issue.axis_weights.items()
            ) / total
            party.issues[issue.issue_id] = float(
                np.clip(value + rng.normal(0.0, 0.05), -1.0, 1.0)
            )
        registry.parties[party.party_id] = party


def _party_axis_stack(registry: PoliticalRegistry) -> tuple[list[int], Array]:
    party_ids = sorted(registry.parties)
    stack = np.stack(
        [
            np.asarray([registry.parties[pid].axes[axis] for axis in axis_ids()])
            for pid in party_ids
        ]
    )
    return party_ids, stack


def _assign_citizen_party_columns(
    registry: PoliticalRegistry, store: PopulationStore, rng: np.random.Generator
) -> None:
    party_ids, party_axes = _party_axis_stack(registry)
    citizen_axes = citizen_axis_matrix(store)
    # Distances normalized by sqrt(n_axes) so scales are dimension-independent.
    scale = float(np.sqrt(len(axis_ids())))
    distances = (
        np.linalg.norm(citizen_axes[:, None, :] - party_axes[None, :, :], axis=2) / scale
    )  # (count, parties), typically ~0.3-0.9
    utilities = np.exp(-((distances / 0.45) ** 2))
    probabilities = utilities / utilities.sum(axis=1, keepdims=True)
    cumulative = np.cumsum(probabilities, axis=1)
    draws = rng.random(store.count)[:, None]
    choice = (draws < cumulative).argmax(axis=1)
    preferred = np.asarray(party_ids, dtype=np.int64)[choice]

    age = -store.column("birth_week").astype(np.float64) / 52.0
    adult = age >= 18.0
    chosen_distance = distances[np.arange(store.count), choice]
    loyalty = np.clip(
        0.25 + 0.60 * (1.0 - chosen_distance) + rng.normal(0.0, 0.12, size=store.count),
        0.0,
        1.0,
    )
    engagement = store.column("political_engagement").astype(np.float64)
    member_probability = 0.26 * engagement * np.clip(1.0 - chosen_distance / 0.75, 0.0, 1.0)
    member = adult & (rng.random(store.count) < member_probability)

    store.set_full_column("preferred_party", preferred.astype(np.int32))
    store.set_full_column(
        "party_member", np.where(member, preferred, 0).astype(np.int32)
    )
    store.set_full_column("party_loyalty", loyalty.astype(np.float32))


# -- characters and branches -------------------------------------------------


def _promote(
    store: PopulationStore,
    ids: IdRegistry,
    characters: CharacterRegistry,
    world: World,
    row: int,
    rng: np.random.Generator,
) -> Character:
    existing = characters.by_row(row)
    if existing is not None:
        return existing
    given = world.given_names[int(store.column("given_name")[row])]
    family = world.family_names[int(store.column("family_name")[row])]
    character = Character(
        character_id=ids.allocate("character"),
        row=row,
        full_name=f"{given} {family}",
        charisma=float(rng.beta(2.2, 2.8)),
        competence=float(rng.beta(2.5, 2.5)),
        integrity=float(rng.beta(2.5, 2.2)),
    )
    set_weight_one(store, row)
    characters.add(character)
    return character


def _member_rows_by_fit(
    registry: PoliticalRegistry, store: PopulationStore, party_id: int
) -> Array:
    """Adult member rows of a party, ordered by ideological fit (best first)."""
    rows = np.flatnonzero(store.column("party_member") == party_id)
    if len(rows) == 0:
        return rows
    age = -store.column("birth_week").astype(np.float64)[rows] / 52.0
    rows = rows[(age >= 25.0) & (age <= 72.0)]
    if len(rows) == 0:
        return rows
    party = registry.parties[party_id]
    party_vector = np.asarray([party.axes[axis] for axis in axis_ids()])
    axes = np.stack(
        [store.column(f"axis_{axis}").astype(np.float64)[rows] for axis in axis_ids()], axis=1
    )
    fit = np.linalg.norm(axes - party_vector[None, :], axis=1)
    return rows[np.argsort(fit, kind="stable")]


def _generate_characters_and_branches(
    registry: PoliticalRegistry,
    world: World,
    store: PopulationStore,
    ids: IdRegistry,
    characters: CharacterRegistry,
    rng: np.random.Generator,
) -> None:
    members_column = store.column("party_member")
    for party_id in sorted(registry.parties):
        party = registry.parties[party_id]
        ranked = _member_rows_by_fit(registry, store, party_id)
        cursor = 0

        def next_row(ranked: Array = ranked) -> int | None:
            nonlocal cursor
            while cursor < len(ranked):
                row = int(ranked[cursor])
                cursor += 1
                if characters.by_row(row) is None:
                    return row
            return None

        leader_row = next_row()
        if leader_row is not None:
            party.leader_id = _promote(store, ids, characters, world, leader_row, rng).character_id
        deputy_row = next_row()
        if deputy_row is not None:
            party.deputy_id = _promote(store, ids, characters, world, deputy_row, rng).character_id

        member_count = int((members_column == party_id).sum())
        national = Branch(
            branch_id=ids.allocate("branch"),
            party_id=party_id,
            level=BranchLevel.NATIONAL,
            region_id=0,
            chair_id=party.leader_id,
            member_count=member_count,
        )
        registry.branches[national.branch_id] = national

        provinces_of = store.column("province")
        districts_of = store.column("district")
        for province in world.provinces:
            count = int(
                ((members_column == party_id) & (provinces_of == province.province_id)).sum()
            )
            if count == 0:
                continue
            chair_row = next_row()
            chair = (
                None
                if chair_row is None
                else _promote(store, ids, characters, world, chair_row, rng).character_id
            )
            branch = Branch(
                branch_id=ids.allocate("branch"),
                party_id=party_id,
                level=BranchLevel.PROVINCE,
                region_id=province.province_id,
                chair_id=chair,
                member_count=count,
            )
            registry.branches[branch.branch_id] = branch
        for district in world.districts:
            count = int(
                ((members_column == party_id) & (districts_of == district.district_id)).sum()
            )
            if count == 0:
                continue
            chair_row = next_row()
            chair = (
                None
                if chair_row is None
                else _promote(store, ids, characters, world, chair_row, rng).character_id
            )
            branch = Branch(
                branch_id=ids.allocate("branch"),
                party_id=party_id,
                level=BranchLevel.DISTRICT,
                region_id=district.district_id,
                chair_id=chair,
                member_count=count,
            )
            registry.branches[branch.branch_id] = branch


# -- organizations -----------------------------------------------------------


def _generate_organizations(
    registry: PoliticalRegistry,
    world: World,
    store: PopulationStore,
    ids: IdRegistry,
    characters: CharacterRegistry,
    rng: np.random.Generator,
) -> None:
    count = store.count
    occupation = store.column("occupation")
    religion = store.column("religion")
    engagement = store.column("political_engagement").astype(np.float64)
    env_axis = store.column("axis_environment").astype(np.float64)
    auth_axis = store.column("axis_authority").astype(np.float64)
    veteran = store.column("military_service") == 3
    age = -store.column("birth_week").astype(np.float64) / 52.0
    adult = age >= 18.0

    from polsim.people.columns import OCCUPATION_SECTORS

    sector = {name: index for index, name in enumerate(OCCUPATION_SECTORS)}
    religions = world.religions

    specs: list[tuple[str, OrganizationKind, dict[str, float], Array]] = [
        (
            "United Industrial Workers",
            OrganizationKind.LABOR_UNION,
            {"economic": -0.7},
            adult
            & np.isin(occupation, (sector["industry"], sector["construction"], sector["transport"]))
            & (rng.random(count) < 0.45),
        ),
        (
            "Public Services Union",
            OrganizationKind.LABOR_UNION,
            {"economic": -0.6},
            adult
            & np.isin(
                occupation,
                (sector["public_administration"], sector["education"], sector["healthcare"]),
            )
            & (rng.random(count) < 0.40),
        ),
        (
            "National Employers' Council",
            OrganizationKind.EMPLOYER_ASSOCIATION,
            {"economic": 0.7},
            adult & (occupation == sector["finance"]) & (rng.random(count) < 0.25),
        ),
        (
            "Farmers' League",
            OrganizationKind.AGRARIAN_ASSOCIATION,
            {"economic": 0.2, "environment": -0.3, "social": 0.3},
            adult & (occupation == sector["agriculture"]) & (rng.random(count) < 0.5),
        ),
        (
            f"Assembly of {religions[1] if len(religions) > 1 else 'Faith'}",
            OrganizationKind.RELIGIOUS,
            {"religion": 0.85, "social": 0.5},
            adult & (religion == 1) & (engagement > 0.3) & (rng.random(count) < 0.30),
        ),
        (
            "Clean Horizon Movement",
            OrganizationKind.ADVOCACY,
            {"environment": 0.9},
            adult & (env_axis > 0.35) & (engagement > 0.45) & (rng.random(count) < 0.35),
        ),
        (
            "Civic Rights Watch",
            OrganizationKind.ADVOCACY,
            {"authority": -0.8},
            adult & (auth_axis < -0.35) & (engagement > 0.45) & (rng.random(count) < 0.30),
        ),
        (
            "Order of Professions",
            OrganizationKind.PROFESSIONAL,
            {"economic": 0.2},
            adult
            & np.isin(occupation, (sector["finance"], sector["technology"]))
            & (rng.random(count) < 0.2),
        ),
        (
            "Veterans' Association",
            OrganizationKind.VETERANS,
            {"military": 0.6, "national": 0.3},
            veteran & (rng.random(count) < 0.5),
        ),
    ]

    membership = store.column("primary_organization").copy()
    for name, kind, axes, mask in specs:
        organization_id = ids.allocate("organization")
        free = mask & (membership == 0)
        rows = np.flatnonzero(free)
        membership[rows] = organization_id
        leader_id: int | None = None
        if len(rows) > 0:
            leader_row = int(rows[int(np.argmax(engagement[rows]))])
            leader_id = _promote(store, ids, characters, world, leader_row, rng).character_id
        registry.organizations[organization_id] = Organization(
            organization_id=organization_id,
            name=name,
            kind=kind,
            axes={axis: float(value) for axis, value in axes.items()},
            leader_id=leader_id,
            member_count=len(rows),
        )
    store.set_full_column("primary_organization", membership.astype(np.int32))


# -- factions ----------------------------------------------------------------


def _character_issue(store: PopulationStore, row: int, issue_id: str) -> float:
    return float(store.column(f"issue_{issue_id}")[row])


def _generate_factions(
    registry: PoliticalRegistry,
    store: PopulationStore,
    ids: IdRegistry,
    characters: CharacterRegistry,
) -> None:
    definitions: list[tuple[str, FactionCategory, dict[str, int]]] = [
        ("Green Caucus", FactionCategory.SINGLE_ISSUE, {"carbon_limits": 1}),
        ("Industry First Bloc", FactionCategory.SINGLE_ISSUE, {"carbon_limits": -1}),
        ("Regionalist Circle", FactionCategory.REGIONAL, {"regional_autonomy": 1}),
        ("Secular Network", FactionCategory.IDEOLOGICAL, {"secular_state": 1}),
        ("Devout Assembly", FactionCategory.RELIGIOUS, {"secular_state": -1}),
    ]
    for name, category, stances in definitions:
        faction = Faction(
            faction_id=ids.allocate("faction"),
            name=name,
            category=category,
            stances=stances,
        )
        registry.factions[faction.faction_id] = faction
        for character_id in characters.all_ids():
            row = characters.get(character_id).row
            aligned = all(
                _character_issue(store, row, issue) * stance > 0.35
                for issue, stance in stances.items()
            )
            if aligned and registry.can_join_faction(character_id, faction.faction_id):
                registry.join_faction(character_id, faction.faction_id)


# -- endorsements ------------------------------------------------------------


def _generate_endorsements(registry: PoliticalRegistry, rng: np.random.Generator) -> None:
    party_ids, party_axes = _party_axis_stack(registry)
    ids_list = axis_ids()
    for organization_id in sorted(registry.organizations):
        organization = registry.organizations[organization_id]
        vector = np.asarray([organization.axes.get(axis, 0.0) for axis in ids_list])
        relevant = np.asarray(
            [1.0 if axis in organization.axes else 0.0 for axis in ids_list]
        )
        if relevant.sum() == 0:
            continue
        distances = np.sqrt(
            (((party_axes - vector[None, :]) ** 2) * relevant[None, :]).sum(axis=1)
        )
        best = int(np.argmin(distances))
        if distances[best] < 0.8:
            registry.endorsements.append(
                Endorsement(
                    organization_id=organization_id,
                    party_id=party_ids[best],
                    strength=float(np.clip(1.0 - distances[best], 0.2, 0.9)),
                    since_week=0,
                )
            )
