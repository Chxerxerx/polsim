"""Deterministic district map geometry (Milestone 2.5 map spike).

Weighted binary-space partition of a rectangular country outline: provinces
are placed first (so each province is a contiguous region), then each
province's districts partition its region, with split positions weighted by
represented population and lightly jittered. The result is an exact
partition — no gaps, no overlaps — which is what the choropleth renderer
needs. Shapes are axis-aligned quadrilaterals for the spike; organic
borders are later visual polish, not simulation state.
"""

from __future__ import annotations

import numpy as np

MAP_WIDTH = 1000.0
MAP_HEIGHT = 700.0

Rect = tuple[float, float, float, float]  # x, y, width, height
Shape = list[tuple[float, float]]


def _rect_shape(rect: Rect) -> Shape:
    x, y, w, h = rect
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def _bsp(
    rect: Rect,
    items: list[tuple[int, float]],
    rng: np.random.Generator,
    out: dict[int, Rect],
) -> None:
    if len(items) == 1:
        out[items[0][0]] = rect
        return
    total = sum(weight for _, weight in items)
    best_index, best_diff = 1, float("inf")
    acc = 0.0
    for index in range(1, len(items)):
        acc += items[index - 1][1]
        diff = abs(acc - (total - acc))
        if diff < best_diff:
            best_diff, best_index = diff, index
    left = items[:best_index]
    right = items[best_index:]
    fraction = sum(weight for _, weight in left) / total
    fraction *= float(rng.uniform(0.94, 1.06))
    fraction = min(max(fraction, 0.15), 0.85)
    x, y, w, h = rect
    if w >= h:
        cut = w * fraction
        _bsp((x, y, cut, h), left, rng, out)
        _bsp((x + cut, y, w - cut, h), right, rng, out)
    else:
        cut = h * fraction
        _bsp((x, y, w, cut), left, rng, out)
        _bsp((x, y + cut, w, h - cut), right, rng, out)


def generate_district_shapes(
    district_ids: list[int],
    district_provinces: list[int],
    district_weights: list[int],
    rng: np.random.Generator,
) -> dict[int, Shape]:
    """Partition the map into per-district polygons, provinces contiguous."""
    province_order: list[int] = []
    grouped: dict[int, list[tuple[int, float]]] = {}
    for district_id, province_id, weight in zip(
        district_ids, district_provinces, district_weights, strict=True
    ):
        if province_id not in grouped:
            grouped[province_id] = []
            province_order.append(province_id)
        grouped[province_id].append((district_id, float(weight)))

    province_rects: dict[int, Rect] = {}
    province_items = [
        (province_id, sum(weight for _, weight in grouped[province_id]))
        for province_id in province_order
    ]
    _bsp((0.0, 0.0, MAP_WIDTH, MAP_HEIGHT), province_items, rng, province_rects)

    shapes: dict[int, Shape] = {}
    for province_id in province_order:
        district_rects: dict[int, Rect] = {}
        _bsp(province_rects[province_id], grouped[province_id], rng, district_rects)
        for district_id, rect in district_rects.items():
            shapes[district_id] = _rect_shape(rect)
    return shapes
