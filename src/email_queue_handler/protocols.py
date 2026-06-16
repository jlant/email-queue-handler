from __future__ import annotations

from typing import Protocol

from .models import Email


class EmailMailer(Protocol):
    """The mailer boundary, as seen by the processor.

    The processor only needs one capability from a mailer: send a single
    email. It does not care how the connection is opened, whether TLS is
    used, or what library is underneath. By depending on this Protocol
    rather than the concrete SmtpMailer, the processor can be tested with a
    FakeMailer that records calls instead of touching the network.

    This is the Dependency Inversion Principle: high-level policy (the
    processor) depends on an abstraction, and the low-level detail (SMTP)
    depends on that same abstraction by satisfying it.
    """

    def send_one(self, email: Email) -> None:
        """Send a single email. Raises on failure."""
        ...


class EmailMarker(Protocol):
    """The repository boundary, as seen by the processor.

    The processor needs exactly one capability from the repository: record
    that a given email has been sent. It does NOT need get_pending here -
    fetching is the service's concern, not the per-email processor's. Keeping
    this interface to the single method the processor uses is interface
    segregation in action: the processor depends only on what it actually
    calls.
    """

    def mark_sent(self, serial_number: int) -> None:
        """Record that the email with this serial number has been sent."""
        ...
