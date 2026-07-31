"""Logging setup (Milestone 1).

Systems log through children of the ``polsim`` logger, for example
``logging.getLogger("polsim.core.sim")``. The library never configures
logging on import; applications and tools call :func:`setup_logging`.
"""

from __future__ import annotations

import logging
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(level: str = "INFO", logfile: Path | None = None) -> logging.Logger:
    """Configure the ``polsim`` root logger. Safe to call repeatedly."""
    logger = logging.getLogger("polsim")
    logger.setLevel(level)
    logger.handlers.clear()
    formatter = logging.Formatter(_FORMAT)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    if logfile is not None:
        file_handler = logging.FileHandler(logfile, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.propagate = False
    return logger
