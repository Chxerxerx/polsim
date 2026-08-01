"""UI walking-skeleton smoke test (offscreen; M2.5).

Boots the real MainWindow with the worker thread, drives it through
new-game → advance → save → advance → load → district selection → map-mode
switch, asserting snapshots flow across the thread boundary. Skipped
automatically when PySide6 is not installed (headless dev setups).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from tests.conftest import FIXED_SEED, SMALL_CONFIG

_TIMEOUT_MS = 30_000


def test_walking_skeleton_full_loop(qtbot: Any, tmp_path: Path) -> None:
    from polsim.ui.main_window import MainWindow
    from polsim.ui.map_view import MapMode

    window = MainWindow(game_config=SMALL_CONFIG, world_seed=FIXED_SEED)
    qtbot.addWidget(window)

    qtbot.waitUntil(lambda: window.current_snapshot() is not None, timeout=_TIMEOUT_MS)
    snapshot = window.current_snapshot()
    assert snapshot is not None
    assert snapshot.week == 0
    assert len(snapshot.districts) == 32
    assert window.map_polygon_count() == 32
    assert snapshot.country_name in window.statusBar().currentMessage()
    assert snapshot.seed_display in window.statusBar().currentMessage()

    with qtbot.waitSignal(window.snapshot_applied, timeout=_TIMEOUT_MS):
        window.advance_week()
    current = window.current_snapshot()
    assert current is not None and current.week == 1

    save_path = str(tmp_path / "skeleton.sqlite")
    with qtbot.waitSignal(window.snapshot_applied, timeout=_TIMEOUT_MS):
        window.save_to(save_path)
    with qtbot.waitSignal(window.snapshot_applied, timeout=_TIMEOUT_MS):
        window.advance_week()
    current = window.current_snapshot()
    assert current is not None and current.week == 2
    with qtbot.waitSignal(window.snapshot_applied, timeout=_TIMEOUT_MS):
        window.load_from(save_path)
    current = window.current_snapshot()
    assert current is not None and current.week == 1  # back at the saved week

    first = current.districts[0]
    window.show_district(first.district_id)
    assert first.name in window.district_panel_text()

    window.set_map_mode(MapMode.MEAN_INCOME)
    assert window.map_polygon_count() == 32

    window.close()
