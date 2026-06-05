import logging

import pytest

from python_service_template.logging import configure_logging
from python_service_template.settings import Settings


def test_configure_logging_sets_level(monkeypatch: pytest.MonkeyPatch) -> None:
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "level", logging.WARNING)

    settings = Settings(log_level="DEBUG")
    configure_logging(settings)

    assert root.level == logging.DEBUG
