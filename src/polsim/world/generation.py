"""Deterministic world and population generation (Milestone 2).

Generates the fictional country: provinces, electoral districts, towns,
name pools, world-specific category labels, and the full weighted citizen
population with correlated demographics. Everything derives from named RNG
streams, so the same seed and settings reproduce the same world
(specification section 31.1).

Structural counts (provinces, districts, towns per district) are generation
content values with documented defaults; they are parameters here so
scenarios can override them later without engine changes.

Weight bookkeeping is exact: represented population is conserved to the
person, nationally and per district (specification section 6.1).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from polsim.core.config import GameConfig, ScenarioConfig
from polsim.core.ids import IdRegistry
from polsim.core.rng import RngManager
from polsim.people.columns import (
    COLUMN_DTYPES,
    EDUCATION_LEVELS,
    EMPLOYMENT_STATUSES,
    HOUSING_TYPES,
    OCCUPATION_SECTORS,
)
from polsim.people.store import PopulationStore
from polsim.world.model import District, Province, Town, World
from polsim.world.names import (
    generate_label_names,
    generate_person_name_pools,
    generate_place_names,
)

Array = NDArray[Any]

DEFAULT_PROVINCES = 10
DEFAULT_DISTRICTS = 32
TOWNS_PER_DISTRICT = (8, 16)  # inclusive range

_E = {name: index for index, name in enumerate(EMPLOYMENT_STATUSES)}
_EDU = {name: index for index, name in enumerate(EDUCATION_LEVELS)}
_H = {name: index for index, name in enumerate(HOUSING_TYPES)}

# Age-bucket population pyramid: (min_age, max_age_exclusive, weight).
_AGE_BUCKETS = (
    (0, 15, 0.16),
    (15, 25, 0.12),
    (25, 40, 0.21),
    (40, 55, 0.20),
    (55, 70, 0.19),
    (70, 95, 0.12),
)

# Weekly income multipliers by education level, on a base of 100.
_EDU_INCOME = np.array([0.65, 0.80, 1.00, 1.10, 1.45, 1.80], dtype=np.float64)


def _largest_remainder(total: int, shares: Array) -> Array:
    """Integer apportionment of ``total`` proportional to ``shares``, exact."""
    shares = shares / shares.sum()
    raw = shares * total
    base = np.floor(raw).astype(np.int64)
    remainder = total - int(base.sum())
    if remainder > 0:
        order = np.argsort(-(raw - base), kind="stable")
        base[order[:remainder]] += 1
    return base


def generate_world(
    scenario: ScenarioConfig,
    game_config: GameConfig,
    rng: RngManager,
    ids: IdRegistry,
    provinces: int = DEFAULT_PROVINCES,
    districts: int = DEFAULT_DISTRICTS,
) -> tuple[World, PopulationStore]:
    """Generate the country and its citizen population."""
    structure_rng = rng.stream("worldgen.structure")
    name_rng = rng.stream("worldgen.names")
    citizen_rng = rng.stream("worldgen.citizens")

    given_names, family_names = generate_person_name_pools(name_rng, 1500, 3000)
    world = World(
        country_name=generate_place_names(name_rng, 1)[0],
        ethnic_groups=generate_label_names(name_rng, 5),
        cultures=generate_label_names(name_rng, 4),
        religions=["none", *generate_label_names(name_rng, 3, suffix="ism"), "folk belief"],
        languages=generate_label_names(name_rng, 3),
        given_names=given_names,
        family_names=family_names,
    )

    # Provinces, each with its own demographic tilts used during generation.
    province_names = generate_place_names(name_rng, provinces)
    province_ids = [ids.allocate("province") for _ in range(provinces)]
    world.provinces = [
        Province(province_id=pid, name=name)
        for pid, name in zip(province_ids, province_names, strict=True)
    ]
    ethnic_tilts = {
        pid: _tilted_probs(structure_rng, base=(0.60, 0.16, 0.10, 0.08, 0.06), strength=6.0)
        for pid in province_ids
    }
    religion_tilts = {
        pid: _tilted_probs(structure_rng, base=(0.34, 0.30, 0.16, 0.12, 0.08), strength=8.0)
        for pid in province_ids
    }

    # Districts allocated across provinces (at least one each).
    district_names = generate_place_names(name_rng, districts)
    per_province = _largest_remainder(
        districts - provinces, np.asarray(structure_rng.random(provinces) + 0.5)
    ) + 1
    district_province: list[int] = []
    for pid, count in zip(province_ids, per_province.tolist(), strict=True):
        district_province.extend([pid] * int(count))
    district_ids = [ids.allocate("district") for _ in range(districts)]
    world.districts = [
        District(district_id=did, name=f"{name} District", province_id=pid)
        for did, name, pid in zip(district_ids, district_names, district_province, strict=True)
    ]

    # Towns: each district gets one urban seat plus a rural/urban mix.
    towns_by_district: dict[int, list[Town]] = {}
    town_size_weights: dict[int, Array] = {}
    total_towns = 0
    for did in district_ids:
        count = int(structure_rng.integers(TOWNS_PER_DISTRICT[0], TOWNS_PER_DISTRICT[1] + 1))
        total_towns += count
        towns_by_district[did] = []
        town_size_weights[did] = np.asarray(structure_rng.lognormal(0.0, 0.9, size=count))
        town_size_weights[did][0] *= 6.0  # the district seat dominates
    town_names = generate_place_names(name_rng, total_towns)
    name_cursor = 0
    for did in district_ids:
        for index in range(len(town_size_weights[did])):
            urban = index == 0 or structure_rng.random() < 0.25
            towns_by_district[did].append(
                Town(
                    town_id=ids.allocate("town"),
                    name=town_names[name_cursor],
                    district_id=did,
                    urban=urban,
                )
            )
            name_cursor += 1
    world.towns = [town for did in district_ids for town in towns_by_district[did]]

    # Represented population per district, conserved exactly.
    district_pop = _largest_remainder(
        scenario.represented_population,
        np.asarray(structure_rng.lognormal(0.0, 0.5, size=districts)),
    )
    citizens_per_district = _largest_remainder(
        game_config.simulated_citizen_target, district_pop.astype(np.float64)
    )
    citizens_per_district = np.maximum(citizens_per_district, 1)
    # Re-fix the total after the minimum-1 floor (only matters at tiny targets).
    overshoot = int(citizens_per_district.sum()) - game_config.simulated_citizen_target
    if overshoot > 0:
        order = np.argsort(-citizens_per_district, kind="stable")
        for index in order[:overshoot]:
            citizens_per_district[index] -= 1

    columns: dict[str, list[Array]] = {name: [] for name in COLUMN_DTYPES}
    district_ranges: dict[int, tuple[int, int]] = {}
    cursor = 0
    for position, did in enumerate(district_ids):
        count = int(citizens_per_district[position])
        represented = int(district_pop[position])
        pid = district_province[position]
        block = _generate_district_citizens(
            citizen_rng,
            count=count,
            represented=represented,
            district_id=did,
            province_id=pid,
            towns=towns_by_district[did],
            town_weights=town_size_weights[did],
            ethnic_tilt=ethnic_tilts[pid],
            religion_tilt=religion_tilts[pid],
            name_pool_sizes=(len(given_names), len(family_names)),
        )
        for name, array in block.items():
            columns[name].append(array)
        district_ranges[did] = (cursor, count)
        cursor += count

    merged = {
        name: np.concatenate(parts).astype(COLUMN_DTYPES[name])
        for name, parts in columns.items()
    }
    ids.allocate_block("citizen", cursor)
    return world, PopulationStore(merged, district_ranges)


def _tilted_probs(
    rng: np.random.Generator, base: tuple[float, ...], strength: float
) -> Array:
    """Perturb a base categorical distribution per province (gamma tilt)."""
    tilt = rng.gamma(np.asarray(base) * strength, 1.0)
    result: Array = tilt / tilt.sum()
    return result


def _choice(rng: np.random.Generator, probs: Array, size: int) -> Array:
    return rng.choice(len(probs), size=size, p=probs / probs.sum())


def _generate_district_citizens(
    rng: np.random.Generator,
    *,
    count: int,
    represented: int,
    district_id: int,
    province_id: int,
    towns: list[Town],
    town_weights: Array,
    ethnic_tilt: Array,
    religion_tilt: Array,
    name_pool_sizes: tuple[int, int],
) -> dict[str, Array]:
    """Vectorized correlated demographics for one district."""
    out: dict[str, Array] = {}

    # Names.
    out["given_name"] = rng.integers(0, name_pool_sizes[0], size=count)
    out["family_name"] = rng.integers(0, name_pool_sizes[1], size=count)

    # Ages from the pyramid, then birth weeks (negative offsets before start).
    bucket_probs = np.asarray([weight for _, _, weight in _AGE_BUCKETS])
    buckets = _choice(rng, bucket_probs, count)
    lows = np.asarray([low for low, _, _ in _AGE_BUCKETS])[buckets]
    highs = np.asarray([high for _, high, _ in _AGE_BUCKETS])[buckets]
    age_years = lows + rng.random(count) * (highs - lows)
    out["birth_week"] = -(age_years * 52.0 + rng.integers(0, 52, size=count)).astype(np.int64)
    age = age_years  # float years, used for correlations below

    # Sex, gender, sexuality.
    out["sex"] = (rng.random(count) < 0.493).astype(np.int8)  # 1 = male
    gender = out["sex"] + (1 - out["sex"]) * 0  # woman=0/man=1 by default
    gender = np.where(rng.random(count) < 0.012, 2, gender)
    out["gender"] = gender
    out["sexuality"] = _choice(rng, np.asarray([0.92, 0.03, 0.04, 0.01]), count)

    # Ethnicity, culture, religion, language with province tilts.
    ethnicity = _choice(rng, ethnic_tilt, count)
    out["ethnicity"] = ethnicity
    culture = np.minimum(ethnicity, 3)
    reshuffle = rng.random(count) < 0.10
    culture = np.where(reshuffle, rng.integers(0, 4, size=count), culture)
    out["culture"] = culture
    religion = _choice(rng, religion_tilt, count)
    secular_youth = (age < 40) & (rng.random(count) < 0.25)
    out["religion"] = np.where(secular_youth, 0, religion)
    language = np.minimum(ethnicity, 2)
    out["language"] = np.where(rng.random(count) < 0.05, rng.integers(0, 3, size=count), language)

    # Education attained, correlated with age.
    education = _choice(rng, np.asarray([0.03, 0.10, 0.34, 0.20, 0.26, 0.07]), count)
    education = np.where(age < 6, _EDU["none"], education)
    education = np.where((age >= 6) & (age < 15), _EDU["primary"], education)
    education = np.where(
        (age >= 15) & (age < 19), np.minimum(education, _EDU["secondary"]), education
    )
    out["education"] = education

    # Employment by age.
    employment = _choice(rng, np.asarray([0.0, 0.0, 0.70, 0.08, 0.07, 0.07, 0.0, 0.08]), count)
    student_age = (age >= 15) & (age < 24) & (rng.random(count) < 0.62)
    employment = np.where(student_age, _E["student"], employment)
    retired = (age >= 65) & (rng.random(count) < 0.88)
    employment = np.where(retired, _E["retired"], employment)
    employment = np.where(age < 15, _E["child"], employment)
    out["employment"] = employment

    # Occupation sector for the working; town/urban assignment first.
    town_index = _choice(rng, town_weights, count)
    town_ids = np.asarray([town.town_id for town in towns])
    town_urban = np.asarray([1 if town.urban else 0 for town in towns], dtype=np.int8)
    out["town"] = town_ids[town_index]
    out["urban"] = town_urban[town_index]
    working = (employment == _E["employed"]) | (employment == _E["self_employed"])
    rural_sector = _choice(
        rng, np.asarray([0.0, 0.30, 0.14, 0.10, 0.10, 0.06, 0.12, 0.01, 0.01, 0.06, 0.06, 0.04]),
        count,
    )
    urban_sector = _choice(
        rng, np.asarray([0.0, 0.01, 0.15, 0.07, 0.14, 0.07, 0.20, 0.06, 0.07, 0.08, 0.09, 0.06]),
        count,
    )
    sector = np.where(out["urban"] == 1, urban_sector, rural_sector)
    out["occupation"] = np.where(working, sector, OCCUPATION_SECTORS.index("none"))

    # Income (weekly), wealth, savings.
    base_income = 100.0 * _EDU_INCOME[education]
    noise = rng.lognormal(0.0, 0.45, size=count)
    income = base_income * noise
    income = np.where(working, income, income * 0.35)
    income = np.where(employment == _E["retired"], base_income * 0.55 * noise, income)
    income = np.where(age < 15, 0.0, income)
    out["income"] = income
    years_active = np.clip(age - 20.0, 0.0, 45.0)
    wealth = income * years_active * rng.lognormal(0.0, 0.8, size=count) * 0.9
    out["wealth"] = np.maximum(wealth, 0.0)
    out["savings"] = out["wealth"] * rng.beta(1.4, 4.0, size=count)

    # Social class from a weighted percentile score.
    score = (
        0.45 * np.argsort(np.argsort(income)) / max(count - 1, 1)
        + 0.35 * np.argsort(np.argsort(out["wealth"])) / max(count - 1, 1)
        + 0.20 * education / (len(EDUCATION_LEVELS) - 1)
    )
    class_edges = np.asarray([0.08, 0.32, 0.55, 0.78, 0.94])
    out["social_class"] = np.searchsorted(class_edges, score).astype(np.int8)

    # Housing.
    owner_prob = np.clip(0.15 + age / 100.0 + out["wealth"] / 500_000.0, 0.0, 0.85)
    draw = rng.random(count)
    housing = np.full(count, _H["renter"], dtype=np.int8)
    housing = np.where(draw < owner_prob, _H["owner"], housing)
    housing = np.where(rng.random(count) < 0.06, _H["social_housing"], housing)
    housing = np.where(rng.random(count) < 0.003, _H["homeless"], housing)
    housing = np.where(age < 20, _H["family_home"], housing)
    out["housing"] = housing

    # Citizenship, military service, disability, health.
    out["citizenship"] = _choice(rng, np.asarray([0.94, 0.03, 0.03]), count)
    veteran = (out["sex"] == 1) & (age >= 40) & (rng.random(count) < 0.18)
    active = (age >= 18) & (age < 40) & (rng.random(count) < 0.015)
    military = np.zeros(count, dtype=np.int8)
    military = np.where(active, 1, military)
    military = np.where(veteran, 3, military)
    out["military_service"] = military
    disability_draw = rng.random(count)
    disability_prob = np.clip((age - 30.0) / 200.0, 0.02, 0.30)
    disability = np.where(disability_draw < disability_prob, 1, 0)
    disability = np.where(disability_draw < disability_prob * 0.3, 2, disability)
    out["disability"] = disability
    health = np.clip(1.0 - age / 140.0 + rng.normal(0.0, 0.08, size=count), 0.05, 1.0)
    out["health"] = health

    # Geography and exact weights.
    out["district"] = np.full(count, district_id)
    out["province"] = np.full(count, province_id)
    base_weight = represented // count
    extra = represented - base_weight * count
    weights = np.full(count, base_weight, dtype=np.int64)
    weights[:extra] += 1
    out["population_weight"] = weights

    return out
