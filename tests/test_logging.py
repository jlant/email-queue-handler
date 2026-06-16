"""Tests for logging configuration.

configure_logging mutates the root logger and creates a log file, so we
isolate both: monkeypatch resets the root logger's handlers/level, and the
log_file points into tmp_path so the test leaves nothing behind.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from email_queue_handler.logging import configure_logging
from email_queue_handler.settings import Settings


def test_configure_logging_sets_level(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "level", logging.WARNING)

    log_file = tmp_path / "test.log"
    settings = Settings(log_level="DEBUG", log_file=str(log_file))
    configure_logging(settings)

    assert root.level == logging.DEBUG


def test_configure_logging_creates_log_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])

    log_file = tmp_path / "nested" / "test.log"
    settings = Settings(log_level="INFO", log_file=str(log_file))
    configure_logging(settings)

    logging.getLogger("eqh-test").info("hello")
    assert log_file.exists()
