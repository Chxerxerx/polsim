from __future__ import annotations

from pathlib import Path

from polsim.core.log import setup_logging


def test_setup_is_idempotent() -> None:
    first = setup_logging("INFO")
    second = setup_logging("INFO")
    assert first is second
    assert len(second.handlers) == 1


def test_file_logging(tmp_path: Path) -> None:
    logfile = tmp_path / "polsim.log"
    logger = setup_logging("DEBUG", logfile)
    assert len(logger.handlers) == 2
    logger.debug("hello from the test suite")
    for handler in logger.handlers:
        handler.flush()
    assert "hello from the test suite" in logfile.read_text(encoding="utf-8")
    setup_logging("INFO")  # release the file handler for cleanup on Windows
