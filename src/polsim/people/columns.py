"""Population column registry and shared category tables (Milestone 2).

Ordinary citizens are rows in a struct-of-arrays store (design doc 02).
This module is the single source of truth for which columns exist, their
dtypes, and the order of shared categorical levels. Columns added in later
milestones (political attributes at M3, memory salience at M5/M6) must be
registered here and covered by a save-schema migration.

World-specific categories (ethnic groups, religions, languages, cultures)
are generated fictional label lists stored on the ``World``; the index
ranges here only fix their column dtypes.
"""

from __future__ import annotations

from functools import cache

from polsim.content.loader import load_axes, load_issues

# (column name, numpy dtype string), fixed order.
BASE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("given_name", "int32"),  # index into World.given_names
    ("family_name", "int32"),  # index into World.family_names
    ("birth_week", "int32"),  # week offset from scenario start (negative = past)
    ("sex", "int8"),
    ("gender", "int8"),
    ("sexuality", "int8"),
    ("ethnicity", "int8"),  # index into World.ethnic_groups
    ("culture", "int8"),  # index into World.cultures
    ("religion", "int8"),  # index into World.religions (0 = none)
    ("language", "int8"),  # index into World.languages
    ("education", "int8"),
    ("occupation", "int8"),
    ("employment", "int8"),
    ("social_class", "int8"),
    ("housing", "int8"),
    ("citizenship", "int8"),
    ("military_service", "int8"),
    ("disability", "int8"),
    ("health", "float32"),  # 0..1
    ("income", "float32"),  # weekly, game currency
    ("wealth", "float32"),
    ("savings", "float32"),
    ("town", "int32"),
    ("district", "int32"),
    ("province", "int32"),
    ("urban", "int8"),
    ("population_weight", "int32"),
)

POLITICAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("preferred_party", "int32"),  # 0 = none
    ("party_member", "int32"),  # 0 = none, else party id
    ("party_loyalty", "float32"),  # toward preferred party, 0..1
    ("political_engagement", "float32"),  # 0..1
    ("political_knowledge", "float32"),  # 0..1
    ("institutional_trust", "float32"),  # 0..1
    ("turnout_propensity", "float32"),  # 0..1
    ("primary_organization", "int32"),  # 0 = none, else organization id
)


@cache
def all_columns() -> tuple[tuple[str, str], ...]:
    """Full column registry: base + political scalars + content axes/issues."""
    axes = tuple((f"axis_{axis.axis_id}", "float32") for axis in load_axes())
    issues = tuple((f"issue_{issue.issue_id}", "float32") for issue in load_issues())
    return BASE_COLUMNS + POLITICAL_COLUMNS + axes + issues


@cache
def column_dtypes() -> dict[str, str]:
    return dict(all_columns())

SEXES: tuple[str, ...] = ("female", "male")
GENDERS: tuple[str, ...] = ("woman", "man", "other")
SEXUALITIES: tuple[str, ...] = ("heterosexual", "homosexual", "bisexual", "other")
EDUCATION_LEVELS: tuple[str, ...] = (
    "none",
    "primary",
    "secondary",
    "vocational",
    "tertiary",
    "postgraduate",
)
EMPLOYMENT_STATUSES: tuple[str, ...] = (
    "child",
    "student",
    "employed",
    "self_employed",
    "unemployed",
    "homemaker",
    "retired",
    "unable",
)
OCCUPATION_SECTORS: tuple[str, ...] = (
    "none",
    "agriculture",
    "industry",
    "construction",
    "retail",
    "transport",
    "services",
    "finance",
    "technology",
    "education",
    "healthcare",
    "public_administration",
)
SOCIAL_CLASSES: tuple[str, ...] = (
    "lower",
    "working",
    "lower_middle",
    "middle",
    "upper_middle",
    "upper",
)
HOUSING_TYPES: tuple[str, ...] = ("family_home", "renter", "owner", "social_housing", "homeless")
CITIZENSHIP_STATUSES: tuple[str, ...] = ("citizen", "permanent_resident", "foreign_resident")
MILITARY_STATUSES: tuple[str, ...] = ("none", "active", "reserve", "veteran")
DISABILITY_LEVELS: tuple[str, ...] = ("none", "minor", "significant")
