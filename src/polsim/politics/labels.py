"""Derived ideological labels (Milestone 3, specification section 7).

Labels are derived, never stored as ground truth: the numerical axis
positions are the substance, the label is a description. Classification is
weighted nearest-prototype over the content-defined label catalog.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from polsim.content.loader import IdeologyLabel, load_axes, load_ideology_labels

Array = NDArray[Any]


def axis_ids() -> tuple[str, ...]:
    return tuple(axis.axis_id for axis in load_axes())


def label_prototypes() -> tuple[tuple[IdeologyLabel, Array], ...]:
    ids = axis_ids()
    return tuple(
        (label, np.asarray([label.axes.get(axis, 0.0) for axis in ids], dtype=np.float64))
        for label in load_ideology_labels()
    )


def classify_axes(axes: Array) -> list[str]:
    """Label ids for an (n, n_axes) position matrix (nearest prototype)."""
    matrix = np.atleast_2d(np.asarray(axes, dtype=np.float64))
    prototypes = label_prototypes()
    stack = np.stack([vector for _, vector in prototypes])  # (labels, n_axes)
    distances = np.linalg.norm(matrix[:, None, :] - stack[None, :, :], axis=2)
    nearest = np.argmin(distances, axis=1)
    return [prototypes[index][0].label_id for index in nearest]


def label_name(label_id: str) -> str:
    for label in load_ideology_labels():
        if label.label_id == label_id:
            return label.name
    raise KeyError(label_id)
