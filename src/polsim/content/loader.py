"""Typed loaders for bundled data-driven content (Milestone 3).

Content ships inside the package (``polsim/content/data``) and is validated
on load; the simulation never interprets free text (specification section
17). Loaders are cached — content is immutable for a given build.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any


class ContentError(ValueError):
    """Raised when bundled content fails validation."""


@dataclass(frozen=True)
class AxisDef:
    axis_id: str
    negative_pole: str
    positive_pole: str


@dataclass(frozen=True)
class IssueDef:
    issue_id: str
    name: str
    area: str
    axis_weights: dict[str, float]


@dataclass(frozen=True)
class IdeologyLabel:
    label_id: str
    name: str
    axes: dict[str, float]
    party_names: tuple[str, ...]


def _read(filename: str) -> Any:
    path = resources.files("polsim.content").joinpath(f"data/{filename}")
    return json.loads(path.read_text(encoding="utf-8"))


@cache
def load_axes() -> tuple[AxisDef, ...]:
    data = _read("issues.json")
    axes = []
    for entry in data["axes"]:
        axis = AxisDef(
            axis_id=str(entry["id"]),
            negative_pole=str(entry["negative_pole"]),
            positive_pole=str(entry["positive_pole"]),
        )
        if not axis.axis_id:
            raise ContentError("axis with empty id")
        axes.append(axis)
    if len({axis.axis_id for axis in axes}) != len(axes):
        raise ContentError("duplicate axis ids")
    return tuple(axes)


@cache
def load_issues() -> tuple[IssueDef, ...]:
    axis_ids = {axis.axis_id for axis in load_axes()}
    data = _read("issues.json")
    issues = []
    for entry in data["issues"]:
        weights = {str(k): float(v) for k, v in entry["axis_weights"].items()}
        unknown = set(weights) - axis_ids
        if unknown:
            raise ContentError(f"issue {entry['id']!r} references unknown axes {sorted(unknown)}")
        if not weights:
            raise ContentError(f"issue {entry['id']!r} has no axis weights")
        if any(not -1.0 <= w <= 1.0 for w in weights.values()):
            raise ContentError(f"issue {entry['id']!r} has weights outside [-1, 1]")
        issues.append(
            IssueDef(
                issue_id=str(entry["id"]),
                name=str(entry["name"]),
                area=str(entry["area"]),
                axis_weights=weights,
            )
        )
    if len({issue.issue_id for issue in issues}) != len(issues):
        raise ContentError("duplicate issue ids")
    return tuple(issues)


@cache
def load_ideology_labels() -> tuple[IdeologyLabel, ...]:
    axis_ids = {axis.axis_id for axis in load_axes()}
    data = _read("ideologies.json")
    labels = []
    for entry in data["labels"]:
        axes = {str(k): float(v) for k, v in entry["axes"].items()}
        unknown = set(axes) - axis_ids
        if unknown:
            raise ContentError(f"label {entry['id']!r} references unknown axes {sorted(unknown)}")
        names = tuple(str(name) for name in entry["party_names"])
        if not names:
            raise ContentError(f"label {entry['id']!r} has no party name patterns")
        labels.append(
            IdeologyLabel(
                label_id=str(entry["id"]), name=str(entry["name"]), axes=axes, party_names=names
            )
        )
    if len({label.label_id for label in labels}) != len(labels):
        raise ContentError("duplicate ideology label ids")
    return tuple(labels)
