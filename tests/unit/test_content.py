"""Bundled content validation (Milestone 3)."""

from __future__ import annotations

import numpy as np

from polsim.content.loader import load_axes, load_ideology_labels, load_issues
from polsim.politics.labels import axis_ids, classify_axes


def test_axes_load() -> None:
    axes = load_axes()
    assert len(axes) == 8
    assert len({axis.axis_id for axis in axes}) == 8


def test_issues_reference_valid_axes_with_bounded_weights() -> None:
    valid = {axis.axis_id for axis in load_axes()}
    issues = load_issues()
    assert len(issues) >= 12
    for issue in issues:
        assert set(issue.axis_weights) <= valid
        assert all(-1.0 <= weight <= 1.0 for weight in issue.axis_weights.values())


def test_label_prototypes_classify_to_themselves() -> None:
    labels = load_ideology_labels()
    ids = axis_ids()
    matrix = np.asarray(
        [[label.axes.get(axis, 0.0) for axis in ids] for label in labels]
    )
    assert classify_axes(matrix) == [label.label_id for label in labels]
