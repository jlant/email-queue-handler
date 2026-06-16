"""Shared test fakes and fixtures.

The fakes here are the payoff of the boundary design. Because the processor
and service depend on the EmailMailer / EmailMarker Protocols (not on smtplib
or pyodbc directly), we can substitute these in-memory fakes and exercise the
real business logic with zero network or database I/O. Tests run in
milliseconds and never touch an external system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import TracebackType

import pytest

from email_queue_handler.models import Email


def make_email(serial: int, recipient: str = "user@example.com") -> Email:
    """Build an Email for tests. Only serial and recipient usually matter, so
    everything else gets a sensible default."""
    return Email(
        serial_number=serial,
        machine="KY01-TEST",
        recipient=recipient,
        queued_at=datetime(2026, 6, 8, 8, 37, 39),
        subject=f"Subject {serial}",
        body=f"Body {serial}",
    )


@dataclass
class FakeMailer:
    """An in-memory stand-in for SmtpMailer.

    Records every email it is asked to send. Can be told to fail on specific
    recipients (to simulate a bad address) or to fail on open (to simulate the
    SMTP server being unreachable). Satisfies the EmailMailer Protocol.
    """

    sent: list[Email] = field(default_factory=list[Email])
    fail_recipients: set[str] = field(default_factory=set[str])
    fail_on_open: bool = False
    opened: bool = False

    def __enter__(self) -> FakeMailer:
        if self.fail_on_open:
            msg = "simulated SMTP connection failure"
            raise ConnectionError(msg)
        self.opened = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.opened = False

    def send_one(self, email: Email) -> None:
        if email.recipient in self.fail_recipients:
            msg = f"simulated send failure for {email.recipient}"
            raise ValueError(msg)
        self.sent.append(email)


@dataclass
class FakeRepository:
    """An in-memory stand-in for EmailRepository.

    Holds a list of pending emails and records which serials get marked sent.
    Can be told to raise on get_pending (to simulate the database being
    unreachable). Satisfies both the read side (get_pending) used by the
    service and the EmailMarker Protocol (mark_sent) used by the processor.
    """

    pending: list[Email] = field(default_factory=list[Email])
    marked: list[int] = field(default_factory=list[int])
    fail_on_fetch: bool = False
    fail_marks: set[int] = field(default_factory=set[int])

    def get_pending(self) -> list[Email]:
        if self.fail_on_fetch:
            msg = "simulated database failure"
            raise ConnectionError(msg)
        return list(self.pending)

    def mark_sent(self, serial_number: int) -> None:
        if serial_number in self.fail_marks:
            msg = f"simulated mark failure for {serial_number}"
            raise RuntimeError(msg)
        self.marked.append(serial_number)


@pytest.fixture
def mailer() -> FakeMailer:
    return FakeMailer()


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()
