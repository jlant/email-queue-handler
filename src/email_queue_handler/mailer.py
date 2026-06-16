from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from types import TracebackType

from .models import Email

logger = logging.getLogger(__name__)


def build_message(send_from: str, to: str, subject: str, body: str) -> EmailMessage:
    """Construct a single RFC-compliant email message."""
    msg = EmailMessage()
    msg["From"] = send_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body or "")
    return msg


class SmtpMailer:
    """Sends one email at a time over an authenticated STARTTLS connection.

    This object is the SMTP boundary: it is the only place that imports
    smtplib and knows about TLS and login. It satisfies the EmailMailer
    Protocol, so the processor can depend on the abstraction and tests can
    substitute a FakeMailer.

    Use it as a context manager so the connection is opened once and always
    closed::

        with SmtpMailer(host, port, send_from, password) as mailer:
            for email in pending:
                handle_email(email, mailer, repo)

    send_one() deliberately does NOT catch exceptions. If a send fails, it
    raises, and the processor's per-email try/except records the failure.
    """

    def __init__(self, host: str, port: int, send_from: str, password: str) -> None:
        self._host = host
        self._port = port
        self._send_from = send_from
        self._password = password
        self._server: smtplib.SMTP | None = None

    def __enter__(self) -> SmtpMailer:  # pragma: no cover
        logger.info("opening SMTP connection host=%s port=%s", self._host, self._port)
        server = smtplib.SMTP(self._host, self._port)
        try:
            server.starttls()
            server.login(self._send_from, self._password)
        except Exception:
            server.close()
            raise
        self._server = server
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:  # pragma: no cover
        if self._server is not None:
            self._server.quit()
            self._server = None
            logger.info("SMTP connection closed")

    def send_one(self, email: Email) -> None:  # pragma: no cover
        """Send a single email. Raises if the connection is not open or the
        send fails."""
        if self._server is None:
            msg = "SmtpMailer.send_one called outside of an open connection"
            raise RuntimeError(msg)
        message = build_message(
            send_from=self._send_from,
            to=email.recipient,
            subject=email.subject,
            body=email.body,
        )
        self._server.send_message(message)
        logger.info("sent email serial=%s to=%s", email.serial_number, email.recipient)


def send_failure_alert(
    host: str,
    port: int,
    send_from: str,
    send_to: str,
    password: str,
    error_msg: str,
) -> bool:  # pragma: no cover
    """Send a single critical-alert email to the administrator.

    This is a separate concern from queue processing: it runs when something
    has gone wrong with the run as a whole (for example, the database is
    unreachable). It opens its own short-lived connection rather than reusing
    the mailer, because the situation that triggers it is exactly when the
    normal path has failed.

    Returns True on success, False on failure, and never raises - if we cannot
    even send the alert, the only thing left to do is log loudly, which we do.
    """
    message = build_message(
        send_from=send_from,
        to=send_to,
        subject="CRITICAL: Email Queue Handler failure",
        body=f"Email Queue Handler alert\n\nTimestamp: {datetime.now()}\nError: {error_msg}",
    )
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(send_from, password)
            server.send_message(message)
        logger.info("failure alert sent to %s", send_to)
        return True
    except Exception:
        logger.exception("failed to send failure alert to %s", send_to)
        return False
