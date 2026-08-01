"""Citizen political attribute generation (Milestone 3).

Fills the political columns for the whole population, vectorized: latent
axis positions correlated with demographics plus province-level political
lean, per-issue positions derived from axis loadings with idiosyncratic
noise (so citizens sharing a label still disagree on individual policies,
specification section 7), and engagement/knowledge/trust/turnout scalars.
Party columns (preference, membership, loyalty) are filled by party
generation once parties exist.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from polsim.content.loader import load_issues
from polsim.people.columns import EMPLOYMENT_STATUSES, OCCUPATION_SECTORS
from polsim.people.store import PopulationStore
from polsim.politics.labels import axis_ids
from polsim.world.model import World

Array = NDArray[Any]

_UNEMPLOYED = EMPLOYMENT_STATUSES.index("unemployed")
_AGRICULTURE = OCCUPATION_SECTORS.index("agriculture")
_INDUSTRY = OCCUPATION_SECTORS.index("industry")
_CONSTRUCTION = OCCUPATION_SECTORS.index("construction")


def _percentile(values: Array) -> Array:
    order = np.argsort(np.argsort(values, kind="stable"), kind="stable")
    return order / max(len(values) - 1, 1)


def fill_political_columns(
    store: PopulationStore, world: World, rng: np.random.Generator
) -> None:
    count = store.count
    age = -store.column("birth_week").astype(np.float64) / 52.0
    age_norm = np.clip((age - 18.0) / 60.0, 0.0, 1.0)
    education = store.column("education").astype(np.float64) / 5.0
    urban = store.column("urban").astype(np.float64)
    religious = (store.column("religion") > 0).astype(np.float64)
    income_pct = _percentile(store.column("income").astype(np.float64))
    wealth_pct = _percentile(store.column("wealth").astype(np.float64))
    occupation = store.column("occupation")
    employment = store.column("employment")
    veteran = (store.column("military_service") == 3).astype(np.float64)
    manual = np.isin(occupation, (_INDUSTRY, _CONSTRUCTION)).astype(np.float64)
    farmer = (occupation == _AGRICULTURE).astype(np.float64)
    unemployed = (employment == _UNEMPLOYED).astype(np.float64)

    provinces = store.column("province")
    province_ids = [province.province_id for province in world.provinces]

    means: dict[str, Array] = {
        "economic": 0.55 * (income_pct - 0.5)
        + 0.35 * (wealth_pct - 0.5)
        - 0.25 * manual
        - 0.20 * unemployed,
        "authority": 0.30 * (age_norm - 0.5) - 0.35 * (education - 0.5) + 0.10 * veteran,
        "national": -0.40 * (education - 0.5) - 0.20 * (urban - 0.5) + 0.25 * (age_norm - 0.5),
        "social": 0.45 * (age_norm - 0.5)
        + 0.30 * religious
        - 0.30 * (education - 0.5)
        - 0.20 * (urban - 0.5)
        - 0.15,
        "religion": 0.85 * religious - 0.45 + 0.20 * (age_norm - 0.5),
        "environment": 0.25 * (education - 0.5)
        + 0.15 * (urban - 0.5)
        - 0.30 * farmer
        - 0.15 * manual,
        "military": 0.20 * (age_norm - 0.5) + 0.35 * veteran,
        "state_structure": np.zeros(count),
    }

    axes_matrix: dict[str, Array] = {}
    for axis in axis_ids():
        lean_full = np.zeros(count)
        for province_id in province_ids:
            lean_full[provinces == province_id] = float(rng.normal(0.0, 0.22))
        base = means.get(axis, np.zeros(count))
        positions = np.clip(base + lean_full + rng.normal(0.0, 0.45, size=count), -1.0, 1.0)
        store.set_full_column(f"axis_{axis}", positions.astype(np.float32))
        axes_matrix[axis] = positions

    for issue in load_issues():
        total_weight = sum(abs(weight) for weight in issue.axis_weights.values())
        derived = np.zeros(count)
        for axis, weight in issue.axis_weights.items():
            derived += weight * axes_matrix[axis]
        derived /= total_weight
        positions = np.clip(derived + rng.normal(0.0, 0.25, size=count), -1.0, 1.0)
        store.set_full_column(f"issue_{issue.issue_id}", positions.astype(np.float32))

    engagement = np.clip(
        rng.beta(2.0, 4.5, size=count) + 0.20 * (education - 0.5) + 0.10 * (age_norm - 0.5),
        0.0,
        1.0,
    )
    knowledge = np.clip(
        0.20 + 0.45 * education + 0.25 * engagement + rng.normal(0.0, 0.10, size=count),
        0.0,
        1.0,
    )
    trust = np.clip(
        0.55 - 0.15 * unemployed - 0.05 * (1.0 - income_pct) + rng.normal(0.0, 0.15, size=count),
        0.0,
        1.0,
    )
    turnout = np.clip(
        0.28 + 0.35 * engagement + 0.20 * age_norm + 0.15 * trust
        + rng.normal(0.0, 0.08, size=count),
        0.02,
        0.98,
    )
    turnout[age < 18.0] = 0.0
    store.set_full_column("political_engagement", engagement.astype(np.float32))
    store.set_full_column("political_knowledge", knowledge.astype(np.float32))
    store.set_full_column("institutional_trust", trust.astype(np.float32))
    store.set_full_column("turnout_propensity", turnout.astype(np.float32))


def citizen_axis_matrix(store: PopulationStore) -> Array:
    """(count, n_axes) float64 matrix of citizen axis positions."""
    return np.stack(
        [store.column(f"axis_{axis}").astype(np.float64) for axis in axis_ids()], axis=1
    )
