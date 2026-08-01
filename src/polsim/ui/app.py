"""Development UI entry point (Milestone 2.5).

Run with ``polsim-ui`` (installed via the ``ui`` extra) or
``python -m polsim.ui``. This is a development shell, not a playable game.
"""

from __future__ import annotations

import argparse
import sys

from polsim.core.config import GameConfig
from polsim.core.log import setup_logging
from polsim.core.seed import parse_seed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--citizens", type=int, default=250_000)
    parser.add_argument("--seed", type=str, default="", help="world seed (display or decimal form)")
    args = parser.parse_args()

    setup_logging("INFO")
    from PySide6.QtWidgets import QApplication

    from polsim.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(
        game_config=GameConfig(simulated_citizen_target=args.citizens),
        world_seed=parse_seed(args.seed) if args.seed.strip() else None,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
