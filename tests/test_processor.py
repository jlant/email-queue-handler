"""Tests for the per-email business rule (processor.handle_email).

These are the highest-value tests in the suite. They encode the correctness
properties the whole design exists to guarantee: send-then-mark ordering,
duplicate-safety, per-email resilience, and validation.
"""

from __future__ import annotations

import pytest
from tests.conftest import FakeMailer, FakeRepository, make_email

from email_queue_handler.processor import handle_email, validate_email


class TestValidateEmail:
    def test_accepts_a_normal_address(self) -> None:
        validate_email(make_email(1, "user@example.com"))  # should not raise

    def test_rejects_empty_recipient(self) -> None:
        with pytest.raises(ValueError, match="recipient is empty"):
            validate_email(make_email(1, ""))

    def test_rejects_whitespace_recipient(self) -> None:
        with pytest.raises(ValueError, match="recipient is empty"):
            validate_email(make_email(1, "   "))

    def test_rejects_address_without_at_sign(self) -> None:
        with pytest.raises(ValueError, match="not a valid address"):
            validate_email(make_email(1, "not-an-address"))


class TestHandleEmail:
    def test_successful_send_marks_sent(self) -> None:
        mailer, repo = FakeMailer(), FakeRepository()
        email = make_email(42)

        result = handle_email(email, mailer=mailer, marker=repo)

        assert result.success is True
        assert result.serial_number == 42
        assert mailer.sent == [email]
        assert repo.marked == [42]

    def test_send_happens_before_mark(self) -> None:
        """The core ordering property: an email is only marked sent AFTER it
        has actually been sent. We prove it by making the send fail and
        confirming the mark never happens."""
        mailer = FakeMailer(fail_recipients={"bad@example.com"})
        repo = FakeRepository()
        email = make_email(7, "bad@example.com")

        result = handle_email(email, mailer=mailer, marker=repo)

        assert result.success is False
        assert mailer.sent == []  # nothing sent
        assert repo.marked == []  # and crucially, nothing marked

    def test_failed_send_returns_failure_not_raises(self) -> None:
        """A bad email must not raise - it returns a failed result so the
        queue can keep going. This is the resilience property."""
        mailer = FakeMailer(fail_recipients={"bad@example.com"})
        repo = FakeRepository()

        result = handle_email(make_email(7, "bad@example.com"), mailer=mailer, marker=repo)

        assert result.success is False
        assert "simulated send failure" in result.reason

    def test_invalid_recipient_never_reaches_mailer(self) -> None:
        """Validation happens before sending, so a malformed address is never
        handed to SMTP at all."""
        mailer, repo = FakeMailer(), FakeRepository()

        result = handle_email(make_email(9, ""), mailer=mailer, marker=repo)

        assert result.success is False
        assert mailer.sent == []
        assert repo.marked == []
        assert "recipient is empty" in result.reason

    def test_mark_failure_after_successful_send_is_reported(self) -> None:
        """If the send succeeds but the mark fails (e.g. DB hiccup), the email
        WAS sent but the result is a failure. Next run will re-send it: a
        duplicate, which is the safe direction to fail."""
        mailer = FakeMailer()
        repo = FakeRepository(fail_marks={5})

        result = handle_email(make_email(5), mailer=mailer, marker=repo)

        assert mailer.sent != []  # it did send
        assert result.success is False  # but we report failure
        assert repo.marked == []  # mark did not record
