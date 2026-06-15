from __future__ import annotations

import logging
import smtplib
from dataclasses import replace
from datetime import datetime
from email.message import EmailMessage

from .models import Email

logger = logging.getLogger(__name__)


def send(
    smtp_server: str,
    smtp_port: int,
    send_from: str,
    password: str,
    emails: list[Email],
) -> list[Email]:
    """Send emails and return a list of processed emails marked as sent."""
    if not emails:
        return []

    processed_emails: list[Email] = []
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(send_from, password)

            for email in emails:
                try:
                    msg = EmailMessage()
                    msg["Subject"] = email.subject
                    msg["From"] = send_from
                    msg["To"] = email.to
                    msg.set_content(email.message or "")
                    server.send_message(msg)
                    logger.info(
                        f"Successfully sent email with serial number: {email.serial_number}"
                    )
                    # Update email as sent
                    processed_email = replace(email, sent=1)
                    processed_emails.append(processed_email)
                except Exception as exc:
                    logging.error(
                        f"Failed to send email with serial number {email.serial_number}: {exc}"
                    )
                    continue

    except Exception as exc:
        logger.error(f"Failed to send emails: {exc}")

    return processed_emails


def send_failure_alert(
    smtp_server: str,
    smtp_port: int,
    send_from: str,
    send_to: str,
    password: str,
    error_msg: str,
) -> bool:
    """Send a failure alert email.

    Returns True if the email was sent successfully, False otherwise.
    Never raises - email failures are logged but do not propagate.
    """
    msg = EmailMessage()
    msg["Subject"] = "CRITICAL: Email Queue Handler Failure"
    msg["From"] = send_from
    msg["To"] = send_to
    msg.set_content(f"Email Queue Handler Alert\n\nTimestamp: {datetime.now()}\nError: {error_msg}")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(send_from, password)
            server.send_message(msg)
            logger.info("failure alert sent to %s", send_to)
            return True
    except Exception as exc:
        logger.error("failed to send failure alert: %s", exc)
        return False
