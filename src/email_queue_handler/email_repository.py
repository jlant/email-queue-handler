from __future__ import annotations

import logging

import pyodbc

from .base_repository import BaseRepository
from .models import Email

logger = logging.getLogger(__name__)

TABLE = "OracleInterface.tblEmailMessage"

# Column names are listed once, here, so the SELECT and the row-mapper cannot
# drift apart. Order matters: it is the contract between the query and
# _row_to_email below.
_COLUMNS = (
    "EmailSerialNumber",
    "Machine",
    "Email_To",
    "EmailDateTime",
    "Subject",
    "Message",
)

_SELECT_COLUMNS = ", ".join(_COLUMNS)


def _row_to_email(row: pyodbc.Row) -> Email:
    """Map one SQL row to an Email.

    Mapping is explicit and positional, matching ``_COLUMNS``. If the query and
    this function ever disagree, you get an obvious error here rather than a
    cryptic failure deep inside a dataclass constructor.
    """
    return Email(
        serial_number=int(row[0]),
        machine=str(row[1]),
        recipient=str(row[2]),
        queued_at=row[3],
        subject=str(row[4]),
        body=str(row[5]) if row[5] is not None else "",
    )


class EmailRepository(BaseRepository):
    """Read pending emails and mark them sent. The only place that knows the
    queue table's schema."""

    def get_pending(self) -> list[Email]:
        """Return every email still waiting to be sent (EmailSent = 0)."""
        query = f"SELECT {_SELECT_COLUMNS} FROM {TABLE} WHERE EmailSent = 0"
        try:
            logger.info("fetching pending emails from %s", TABLE)
            with self._connection_factory() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
            emails = [_row_to_email(row) for row in rows]
            logger.info("fetched %d pending email(s)", len(emails))
            return emails
        except pyodbc.Error:
            logger.exception("failed fetching pending emails")
            raise

    def mark_sent(self, serial_number: int) -> None:
        """Mark a single email as sent.

        Deliberately narrow: it only ever sets EmailSent = 1 for one row,
        identified by its unique serial number. It never touches the recipient,
        subject, body, or any other column, so a bug elsewhere in the program
        cannot corrupt the original message. Commits its own transaction so the
        "sent" fact is durable the instant the email goes out.
        """
        query = f"UPDATE {TABLE} SET EmailSent = 1 WHERE EmailSerialNumber = ?"
        try:
            with self._connection_factory() as conn:
                cursor = conn.cursor()
                cursor.execute(query, serial_number)
                conn.commit()
            logger.info("marked email sent serial=%s", serial_number)
        except pyodbc.Error:
            logger.exception("failed marking email sent serial=%s", serial_number)
            raise
