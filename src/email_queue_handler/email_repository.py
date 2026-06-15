from __future__ import annotations

import logging

import pyodbc

from .base_repository import BaseRepository
from .models import Email

logger = logging.getLogger(__name__)


class EmailRepository(BaseRepository):
    def get_all(self) -> list[Email]:
        """Fetches all emails"""
        query = """
            SELECT
                EmailSerialNumber AS serial_number,
                Machine AS machine
                Email_To AS to,
                EmailDateTime AS, datetime
                Subject AS subject,
                Message AS message,
                EmailSent AS sent
            FROM tblEmailMessage
        """
        try:
            logging.info("Fetching emails from tblEmailMessage...")
            with self._connection_factory() as conn, conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                # Use the base repository helper function to turn rows into dicts, then unpack
                return [Email(**self._row_to_dict(cursor, r)) for r in rows]
        except pyodbc.Error as exc:
            logging.error(f"Query execution failed: {exc}")
            raise

    def get_unsent(self) -> list[Email]:
        """Fetches all unsent email messages"""
        query = """
            SELECT
                EmailSerialNumber AS serial_number,
                Machine AS machine
                Email_To AS to,
                EmailDateTime AS, datetime
                Subject AS subject,
                Message AS message,
            FROM tblEmailMessage
            WHERE email_sent = 0
        """
        try:
            logging.info("Fetching unsent emails from tblEmailMessage...")
            with self._connection_factory() as conn, conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                # Use the base repository helper function to turn rows into dicts, then unpack
                return [Email(**self._row_to_dict(cursor, r)) for r in rows]
        except pyodbc.Error as exc:
            logging.error(f"Query execution failed: {exc}")
            raise

    def get_by_serial_number(self, serial_number: int) -> Email | None:
        """Fetches a single email message matching a serial number."""
        query = """
            SELECT UserID AS user_id, FirstName AS first_name, email_address
            FROM Users WHERE UserID = ?
        """
        query = """
            SELECT
                EmailSerialNumber AS serial_number,
                Machine AS machine
                Email_To AS to,
                EmailDateTime AS, datetime
                Subject AS subject,
                Message AS message,
                EmailSent AS sent
            FROM tblEmailMessage
            WHERE serial_number = ?
        """
        try:
            logging.info("Fetching email messages by serial number from tblEmailMessage...")
            with self._connection_factory() as conn, conn.cursor() as cursor:
                cursor.execute(query, (serial_number,))
                row = cursor.fetchone()
                if not row:
                    return None
                # Use the base repository helper function to turn rows into dicts, then unpack
                return Email(**self._row_to_dict(cursor, row))
        except pyodbc.Error as exc:
            logging.error(f"Query execution failed: {exc}")
            raise

    def update(self, email: Email) -> None:
        """Update an email."""
        query = """
            UPDATE tblEmailMessage
            SET Machine = ?,
                Email_To = ?,
                EmailDateTime = ?,
                Subject = ?,
                Message = ?,
                EmailSent = ?
            WHERE EmailSerialNumber = ?
        """
        try:
            logging.info(f"Updating email with serial number {email.serial_number}")
            with self._connection_factory() as conn, conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        email.machine,
                        email.to,
                        email.datetime,
                        email.subject,
                        email.message,
                        email.sent,
                        email.serial_number,
                    ),
                )
                conn.commit()
        except pyodbc.Error as exc:
            logging.error(f"Query execution failed: {exc}")
            raise

    def update_many(self, emails: list[Email]) -> None:
        """
        Update emails in a batch transaction.
        """
        if not emails:
            logging.info("No emails to update.")
            return

        query = """
            UPDATE tblEmailMessage
            SET Machine = ?,
                Email_To = ?,
                EmailDateTime = ?,
                Subject = ?,
                Message = ?,
                EmailSent = ?
            WHERE EmailSerialNumber = ?
        """
        params_list = [
            (
                email.machine,
                email.to,
                email.datetime,
                email.subject,
                email.message,
                email.sent,
                email.serial_number,
            )
            for email in emails
        ]

        try:
            logging.info("Updating emails...")
            with self._connection_factory() as conn, conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
        except pyodbc.Error as exc:
            logging.error(f"Query execution failed: {exc}")
            raise
