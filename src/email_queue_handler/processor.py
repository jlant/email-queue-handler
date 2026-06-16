from __future__ import annotations

import logging

from .models import Email, EmailResult
from .protocols import EmailMailer, EmailMarker

logger = logging.getLogger(__name__)


def validate_email(email: Email) -> None:
    """Reject obviously unsendable emails before we hand them to SMTP.

    This is a cheap guard, not full RFC 5322 validation. Its job is to catch
    the common bad-data cases (null/blank recipient) and turn them into a
    clear, logged failure instead of an obscure exception from deep inside
    smtplib. Anything stricter (real address syntax checking) can be added
    here later without the rest of the system changing.
    """
    if not email.recipient or not email.recipient.strip():
        msg = "recipient is empty"
        raise ValueError(msg)
    if "@" not in email.recipient:
        msg = f"recipient is not a valid address: {email.recipient!r}"
        raise ValueError(msg)


def handle_email(email: Email, mailer: EmailMailer, marker: EmailMarker) -> EmailResult:
    """Process exactly one email: validate, send, then mark sent.

    This is the single most important function in the service, and the
    ordering of its three steps encodes the system's core correctness rule:

        send FIRST, mark sent SECOND - never the other way around.

    If the process dies between send and mark, the email stays EmailSent = 0
    and will be re-sent on the next run. That is a duplicate email: annoying,
    but recoverable and visible. The opposite ordering (mark then send) would
    risk marking an email sent that never actually went out - silent data
    loss, which is far worse. We always fail toward the recoverable error.

    Each email is wrapped in its own try/except so that one bad recipient
    cannot halt the queue. A failure here returns an EmailResult with
    success=False; it does not raise. The caller (the service) decides what to
    do with a queue full of results.
    """
    try:
        validate_email(email)
        mailer.send_one(email)
        # Only reached if send_one did NOT raise. Mark sent in its own
        # transaction so the "sent" fact is durable immediately.
        marker.mark_sent(email.serial_number)
        logger.info("email processed serial=%s", email.serial_number)
        return EmailResult(email.serial_number, success=True, reason="sent")
    except Exception as exc:
        # TODO: poison-message handling. For now we log and leave the row at
        # EmailSent = 0, so a permanently-bad email will be retried every run.
        # This is a known, accepted limitation for v1 (see README).
        logger.exception("email failed serial=%s", email.serial_number)
        return EmailResult(email.serial_number, success=False, reason=str(exc))
