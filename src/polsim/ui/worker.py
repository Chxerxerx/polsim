"""Simulation worker for the UI (Milestone 2.5).

The worker is a QObject moved to a dedicated QThread; the main window
invokes it exclusively through queued signal connections and receives
immutable :class:`WorldSnapshot` objects back. The UI thread never touches
the ``Simulation`` directly (design doc 01: command in, snapshot out).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from polsim.core.config import GameConfig
from polsim.core.sim import Simulation
from polsim.save import load_game, save_game
from polsim.ui.viewmodels import build_snapshot

_LOG = logging.getLogger("polsim.ui.worker")


class SimulationWorker(QObject):
    """Owns the Simulation on the worker thread."""

    snapshot_ready = Signal(object)  # WorldSnapshot
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._sim: Simulation | None = None

    @Slot(object)
    def new_game(self, params: object) -> None:
        try:
            if not isinstance(params, tuple) or len(params) != 2:
                raise ValueError(f"invalid new-game parameters: {params!r}")
            raw_seed, raw_config = params
            world_seed = raw_seed if isinstance(raw_seed, int) else None
            game_config = raw_config if isinstance(raw_config, GameConfig) else None
            self._sim = Simulation.new_game(game_config=game_config, world_seed=world_seed)
            self._emit_snapshot()
        except Exception as exc:  # surfaced to the UI, never swallowed
            _LOG.exception("new_game failed")
            self.error.emit(f"New game failed: {exc}")

    @Slot()
    def advance_week(self) -> None:
        if self._sim is None:
            return
        try:
            self._sim.advance_week()
            self._emit_snapshot()
        except Exception as exc:
            _LOG.exception("advance_week failed")
            self.error.emit(f"Turn failed: {exc}")

    @Slot(str)
    def save(self, path: str) -> None:
        if self._sim is None:
            return
        try:
            save_game(self._sim, Path(path))
            self._emit_snapshot()
        except Exception as exc:
            _LOG.exception("save failed")
            self.error.emit(f"Save failed: {exc}")

    @Slot(str)
    def load(self, path: str) -> None:
        try:
            self._sim = load_game(Path(path))
            self._emit_snapshot()
        except Exception as exc:
            _LOG.exception("load failed")
            self.error.emit(f"Load failed: {exc}")

    def _emit_snapshot(self) -> None:
        if self._sim is not None:
            self.snapshot_ready.emit(build_snapshot(self._sim))
