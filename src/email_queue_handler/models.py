from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Email:
    """A single email message read from the queue table.

    This is a read model: it represents one row of ``tblEmailMessage`` that
    still needs to be sent. Rows are only ever fetched when ``EmailSent = 0``,
    so there is deliberately no ``sent`` field here - "unsent" is implied by
    the fact that we have the object at all. The act of sending is recorded by
    calling ``EmailRepository.mark_sent(serial_number)``, not by mutating this
    object.

    Field names are domain names, not database column names. The mapping from
    SQL columns to these fields lives in the repository (the boundary), which
    is the only place that should know about the table's schema.
    """

    serial_number: int
    machine: str
    recipient: str
    queued_at: datetime
    subject: str
    body: str


@dataclass(frozen=True)
class EmailResult:
    """The outcome of attempting to process one email.

    Returned by the processor for every email it handles - success or failure -
    so the service can log a per-email summary and the test suite can assert on
    outcomes without inspecting logs.
    """

    serial_number: int
    success: bool
    reason: str
