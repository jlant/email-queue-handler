from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from .settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class Service:
    settings: Settings
    started: bool = field(default=False, init=False)

    def start(self) -> None:
        logger.info("starting service app=%s env=%s", self.settings.app_name, self.settings.env)
        self.started = True

    def run(self) -> None:
        if not self.started:
            msg = "service must be started before run()"
            raise RuntimeError(msg)

        logger.info(
            "running service app=%s env=%s run_seconds=%s",
            self.settings.app_name,
            self.settings.env,
            self.settings.run_seconds,
        )

        time.sleep(self.settings.run_seconds)

    def stop(self) -> None:
        if not self.started:
            logger.warning("stop() called but service is not running")
            return
        logger.info(
            "stopping service app=%s env=%s",
            self.settings.app_name,
            self.settings.env,
        )
        self.started = False
