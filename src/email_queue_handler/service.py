from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .database import get_connection
from .email_repository import EmailRepository
from .mailer import SmtpMailer, send_failure_alert
from .models import EmailResult
from .processor import handle_email
from .settings import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunSummary:
    """The outcome of a single run cycle.

    ``run_failed`` is True only for run-level failures (database unreachable,
    SMTP login refused) - the kind that break the whole pass. Individual email
    failures are counted in ``failed`` but do NOT set ``run_failed``; one bad
    recipient is not a failed run.
    """

    fetched: int = 0
    sent: int = 0
    failed: int = 0
    run_failed: bool = False


@dataclass
class Service:
    settings: Settings
    started: bool = field(default=False, init=False)

    def start(self) -> None:
        logger.info("starting service app=%s env=%s", self.settings.app_name, self.settings.env)
        self.started = True

    def _run_cycle(self) -> RunSummary:
        """Run exactly one pass over the queue.

        One database connection and one SMTP connection are opened for the
        whole pass, then each pending email is processed individually. The
        send-then-mark ordering and per-email resilience live in
        ``handle_email``; this method's job is orchestration and the
        separation of the two failure kinds.
        """
        settings = self.settings
        repo = EmailRepository(connection_factory=lambda: get_connection(settings))

        try:
            pending = repo.get_pending()
        except Exception as exc:
            # Run-level failure: we could not even read the queue. Alert and
            # report the run as failed.
            self._alert(f"failed to read email queue: {exc}")
            return RunSummary(run_failed=True)

        if not pending:
            logger.info("no pending emails")
            return RunSummary(fetched=0)

        results: list[EmailResult] = []
        try:
            with SmtpMailer(
                host=settings.email_smtp_server,
                port=settings.email_smtp_port,
                send_from=settings.email_send_from,
                password=settings.email_password,
            ) as mailer:
                for email in pending:
                    result = handle_email(email, mailer=mailer, marker=repo)
                    results.append(result)
        except Exception as exc:
            # Run-level failure: the SMTP connection itself failed (bad host,
            # login refused, TLS error). Nothing in this pass could be sent.
            self._alert(f"failed to open SMTP connection: {exc}")
            return RunSummary(fetched=len(pending), run_failed=True)

        sent = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        logger.info("run complete fetched=%d sent=%d failed=%d", len(pending), sent, failed)
        return RunSummary(fetched=len(pending), sent=sent, failed=failed)

    def _alert(self, error_msg: str) -> None:
        """Send a critical alert to the administrator. Never raises."""
        logger.error("run-level failure: %s", error_msg)
        if not self.settings.email_send_to:
            logger.warning("no admin address configured (email_send_to); skipping alert")
            return
        send_failure_alert(
            host=self.settings.email_smtp_server,
            port=self.settings.email_smtp_port,
            send_from=self.settings.email_send_from,
            send_to=self.settings.email_send_to,
            password=self.settings.email_password,
            error_msg=error_msg,
        )

    def run(self) -> RunSummary:
        if not self.started:
            msg = "service must be started before run()"
            raise RuntimeError(msg)
        logger.info("running service app=%s env=%s", self.settings.app_name, self.settings.env)
        return self._run_cycle()

    def stop(self) -> None:
        if not self.started:
            logger.warning("stop() called but service is not running")
            return
        logger.info("stopping service app=%s env=%s", self.settings.app_name, self.settings.env)
        self.started = False
