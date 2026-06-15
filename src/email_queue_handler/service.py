from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from . import emailer
from .email_repository import EmailRepository
from .settings import Settings
from .sqlserver_db import get_connection

logger = logging.getLogger(__name__)


@dataclass
class Service:
    settings: Settings
    started: bool = field(default=False, init=False)

    def start(self) -> None:
        logger.info("starting service app=%s env=%s", self.settings.app_name, self.settings.env)
        self.started = True

    def _run_cycle(self) -> None:
        """ """
        # Instantiate a repo with a database connection
        repo = EmailRepository(connection_factory=lambda: get_connection(self.settings))
        try:
            # Get all unsent emails
            unsent_emails = repo.get_unsent()

            if not unsent_emails:
                return

            # Send each email and mark as sent
            sent_emails = emailer.send(
                smtp_server=self.settings.email_smtp_server,
                smtp_port=self.settings.email_smtp_port,
                send_from=self.settings.email_send_from,
                password=self.settings.email_password,
                emails=unsent_emails,
            )

            # Step 3: Update the database table with emails marked as sent
            repo.update_many(sent_emails)

        except Exception as exc:
            logging.error(f"{exc}")

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

        deadline = time.monotonic() + self.settings.run_seconds

        while True:
            self._run_cycle()
            if time.monotonic() >= deadline:
                break

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
