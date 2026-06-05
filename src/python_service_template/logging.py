from __future__ import annotations

import logging

from .settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure application logging once at startup."""
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    logging.getLogger().info("logging configured", extra={"level": settings.log_level})
