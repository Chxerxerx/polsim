"""District map renderer behind the map interface (Milestone 2.5 spike).

QGraphicsView vector polygons with choropleth modes, hover tooltips, and
click-to-select — the initial implementation of ADR-001's map-renderer
abstraction. An accelerated renderer can replace this class later without
touching the rest of the UI.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPen, QPolygonF, QResizeEvent
from PySide6.QtWidgets import QGraphicsPolygonItem, QGraphicsScene, QGraphicsView, QWidget

from polsim.ui.viewmodels import DistrictView, WorldSnapshot

_LOW = (231, 238, 245)
_HIGH = (26, 84, 158)


class MapMode(Enum):
    POPULATION = "Population"
    MEAN_INCOME = "Mean income"
    URBAN_SHARE = "Urban share"


def _mode_value(view: DistrictView, mode: MapMode) -> float:
    if mode is MapMode.POPULATION:
        return float(view.population)
    if mode is MapMode.MEAN_INCOME:
        return view.mean_income
    return view.urban_share


def _scale_color(fraction: float) -> QColor:
    return QColor(
        int(_LOW[0] + (_HIGH[0] - _LOW[0]) * fraction),
        int(_LOW[1] + (_HIGH[1] - _LOW[1]) * fraction),
        int(_LOW[2] + (_HIGH[2] - _LOW[2]) * fraction),
    )


class DistrictMapView(QGraphicsView):
    """Choropleth district map."""

    district_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._items: dict[int, QGraphicsPolygonItem] = {}
        self._mode = MapMode.POPULATION
        self._snapshot: WorldSnapshot | None = None

    def polygon_count(self) -> int:
        return len(self._items)

    def mode(self) -> MapMode:
        return self._mode

    def set_mode(self, mode: MapMode) -> None:
        self._mode = mode
        self._apply_colors()

    def set_snapshot(self, snapshot: WorldSnapshot) -> None:
        rebuild = {view.district_id for view in snapshot.districts} != set(self._items)
        self._snapshot = snapshot
        if rebuild:
            self._rebuild(snapshot)
            self._scene.setSceneRect(0.0, 0.0, snapshot.map_width, snapshot.map_height)
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._apply_colors()

    def _rebuild(self, snapshot: WorldSnapshot) -> None:
        self._scene.clear()
        self._items = {}
        pen = QPen(QColor(255, 255, 255))
        pen.setWidthF(1.5)
        for view in snapshot.districts:
            polygon = QPolygonF()
            for x, y in view.shape:
                polygon.append(QPointF(x, y))
            item = self._scene.addPolygon(polygon, pen)
            item.setData(0, view.district_id)
            self._items[view.district_id] = item

    def _apply_colors(self) -> None:
        if self._snapshot is None or not self._items:
            return
        values = {
            view.district_id: _mode_value(view, self._mode) for view in self._snapshot.districts
        }
        low = min(values.values())
        high = max(values.values())
        span = (high - low) or 1.0
        for view in self._snapshot.districts:
            fraction = (values[view.district_id] - low) / span
            item = self._items[view.district_id]
            item.setBrush(QBrush(_scale_color(fraction)))
            item.setToolTip(
                f"{view.name} ({view.province_name})\n"
                f"{self._mode.value}: {values[view.district_id]:,.1f}"
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        if item is not None:
            district_id = item.data(0)
            if isinstance(district_id, int):
                self.district_clicked.emit(district_id)
        super().mousePressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._snapshot is not None:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
