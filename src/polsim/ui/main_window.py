"""Main window: shell, toolbar, map, district dock, worker wiring (M2.5).

Walking skeleton only — a development shell around the simulation, clearly
not gameplay. All simulation access goes through queued signals to the
worker thread; the UI renders snapshots (design doc 01).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QToolBar,
    QWidget,
)

from polsim.core.config import GameConfig
from polsim.core.seed import parse_seed
from polsim.ui.map_view import DistrictMapView, MapMode
from polsim.ui.panels import DistrictInfoPanel
from polsim.ui.viewmodels import WorldSnapshot
from polsim.ui.worker import SimulationWorker

_SAVE_FILTER = "polsim saves (*.sqlite)"


class MainWindow(QMainWindow):
    """Development shell window."""

    _request_new_game = Signal(object)
    _request_advance = Signal()
    _request_save = Signal(str)
    _request_load = Signal(str)
    snapshot_applied = Signal(object)

    def __init__(
        self,
        game_config: GameConfig | None = None,
        world_seed: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._game_config = game_config or GameConfig()
        self._snapshot: WorldSnapshot | None = None
        self.setWindowTitle("polsim — development build (not a playable game yet)")
        self.resize(1200, 800)

        self._map = DistrictMapView(self)
        self.setCentralWidget(self._map)
        self._map.district_clicked.connect(self.show_district)

        self._panel = DistrictInfoPanel(self)
        dock = QDockWidget("District", self)
        dock.setWidget(self._panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        new_action = QAction("New Game", self)
        new_action.triggered.connect(self._on_new_game_dialog)
        toolbar.addAction(new_action)
        self._advance_action = QAction("Advance Week", self)
        self._advance_action.setEnabled(False)
        self._advance_action.triggered.connect(self.advance_week)
        toolbar.addAction(self._advance_action)
        save_action = QAction("Save…", self)
        save_action.triggered.connect(self._on_save_dialog)
        toolbar.addAction(save_action)
        load_action = QAction("Load…", self)
        load_action.triggered.connect(self._on_load_dialog)
        toolbar.addAction(load_action)
        self._mode_box = QComboBox(self)
        for mode in MapMode:
            self._mode_box.addItem(mode.value, userData=mode)
        self._mode_box.currentIndexChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_box)

        self._thread = QThread(self)
        self._worker = SimulationWorker()
        self._worker.moveToThread(self._thread)
        self._request_new_game.connect(self._worker.new_game)
        self._request_advance.connect(self._worker.advance_week)
        self._request_save.connect(self._worker.save)
        self._request_load.connect(self._worker.load)
        self._worker.snapshot_ready.connect(self._apply_snapshot)
        self._worker.error.connect(self._on_error)
        self._thread.start()
        self.statusBar().showMessage("Generating world…")
        self._request_new_game.emit((world_seed, self._game_config))

    # -- state / accessors --------------------------------------------------

    def current_snapshot(self) -> WorldSnapshot | None:
        return self._snapshot

    def map_polygon_count(self) -> int:
        return self._map.polygon_count()

    def district_panel_text(self) -> str:
        return self._panel.district_text()

    # -- commands -----------------------------------------------------------

    def advance_week(self) -> None:
        self._advance_action.setEnabled(False)
        self._request_advance.emit()

    def save_to(self, path: str) -> None:
        self._request_save.emit(path)

    def load_from(self, path: str) -> None:
        self._request_load.emit(path)

    def set_map_mode(self, mode: MapMode) -> None:
        self._mode_box.setCurrentIndex(list(MapMode).index(mode))
        self._map.set_mode(mode)

    @Slot(int)
    def show_district(self, district_id: int) -> None:
        if self._snapshot is not None:
            self._panel.show_district(self._snapshot.district(district_id))

    # -- worker results -----------------------------------------------------

    @Slot(object)
    def _apply_snapshot(self, snapshot: object) -> None:
        if not isinstance(snapshot, WorldSnapshot):
            return
        self._snapshot = snapshot
        self._map.set_snapshot(snapshot)
        self.statusBar().showMessage(
            f"{snapshot.country_name} — Week {snapshot.week} ({snapshot.date_iso}) — "
            f"{snapshot.citizen_count:,} simulated citizens representing "
            f"{snapshot.represented_population:,} — seed {snapshot.seed_display}"
        )
        self._advance_action.setEnabled(True)
        self.snapshot_applied.emit(snapshot)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        self.statusBar().showMessage(message)
        self._advance_action.setEnabled(self._snapshot is not None)

    # -- dialogs ------------------------------------------------------------

    def _on_new_game_dialog(self) -> None:
        text, accepted = QInputDialog.getText(
            self, "New Game", "World seed (leave empty for a random seed):"
        )
        if not accepted:
            return
        seed = parse_seed(text) if text.strip() else None
        self.statusBar().showMessage("Generating world…")
        self._request_new_game.emit((seed, self._game_config))

    def _on_save_dialog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save game", filter=_SAVE_FILTER)
        if path:
            self.save_to(path)

    def _on_load_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load game", filter=_SAVE_FILTER)
        if path:
            self.load_from(path)

    def _on_mode_changed(self, index: int) -> None:
        mode = self._mode_box.itemData(index)
        if isinstance(mode, MapMode):
            self._map.set_mode(mode)

    # -- lifecycle ----------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        self._thread.quit()
        self._thread.wait(5000)
        super().closeEvent(event)
