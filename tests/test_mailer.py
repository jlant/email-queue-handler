"""Tests for the mailer boundary's pure logic.

We test build_message because it is pure logic - it constructs an
EmailMessage from strings with no I/O. The actual sending methods
(SmtpMailer.__enter__/__exit__/send_one and send_failure_alert) talk to a
real SMTP server and are marked `# pragma: no cover`; they are verified by
live deployment testing, not unit tests.
"""

from __future__ import annotations

from email_queue_handler.mailer import build_message


def test_build_message_sets_headers_and_body() -> None:
    msg = build_message(
        send_from="noreply@llflex.com",
        to="user@llflex.com",
        subject="OverRide_Form_KeyDown",
        body="An override was performed.",
    )
    assert msg["From"] == "noreply@llflex.com"
    assert msg["To"] == "user@llflex.com"
    assert msg["Subject"] == "OverRide_Form_KeyDown"
    assert msg.get_content().strip() == "An override was performed."


def test_build_message_handles_empty_body() -> None:
    msg = build_message(send_from="a@x.com", to="b@y.com", subject="S", body="")
    # An empty body must not raise and must produce a valid (empty) content.
    assert msg["Subject"] == "S"
    assert msg.get_content().strip() == ""
