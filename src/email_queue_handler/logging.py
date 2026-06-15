from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from .settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure application logging once at startup.

    Attaches two handlers to the root logger:
    - StreamHandler: writes to console (useful for manual runs)
    - RotatingFileHandler: writes to the configured log file
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler - for interactive use
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)

    # File handler - for scheduled task runs
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    logging.getLogger(__name__).info(
        "logging configured log_level=%s log_file=%s",
        settings.log_level,
        settings.log_file,
    )

    # Suppress paramiko internal logs and log at warning level instead
    logging.getLogger("paramiko").setLevel(logging.WARNING)
