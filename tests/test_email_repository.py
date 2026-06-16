"""Tests for the SQL boundary (EmailRepository).

We don't need a real database to verify that the repository issues the right
SQL and maps rows into Email objects correctly. A fake connection records the
queries and parameters it receives and returns canned rows. This catches the
class of bug that broke the original draft (wrong column names, bad WHERE
clauses, column/field mismatches) without a SQL Server instance.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from email_queue_handler.email_repository import EmailRepository

if TYPE_CHECKING:
    import pyodbc

Row = tuple[Any, ...]


class FakeCursor:
    def __init__(self, rows: list[Row]) -> None:
        self._rows: list[Row] = rows
        self.executed: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, query: str, *params: object) -> None:
        self.executed.append((query, params))

    def fetchall(self) -> list[Row]:
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[Row]) -> None:
        self.cursor_obj = FakeCursor(rows)
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1


def _factory(
    conn: FakeConnection,
) -> Callable[[], AbstractContextManager[pyodbc.Connection]]:
    @contextmanager
    def factory() -> Generator[pyodbc.Connection, None, None]:
        # FakeConnection duck-types as a pyodbc.Connection for the methods the
        # repository uses (cursor, commit). cast tells the type checker we
        # accept responsibility for that substitution; it is a no-op at runtime.
        yield cast("pyodbc.Connection", conn)

    return factory


def test_get_pending_maps_rows_to_emails() -> None:
    rows: list[Row] = [
        (16336, "KY01-SPL022", "a@llflex.com", datetime(2026, 6, 8, 8, 37, 39), "Subj", "Body"),
        (16337, "KY02-SPL023", "b@llflex.com", datetime(2026, 6, 8, 9, 0, 0), "Subj2", "Body2"),
    ]
    conn = FakeConnection(rows)
    repo = EmailRepository(connection_factory=_factory(conn))

    emails = repo.get_pending()

    assert len(emails) == 2
    assert emails[0].serial_number == 16336
    assert emails[0].recipient == "a@llflex.com"
    assert emails[0].subject == "Subj"
    assert emails[1].serial_number == 16337


def test_get_pending_filters_on_emailsent_zero() -> None:
    conn = FakeConnection([])
    repo = EmailRepository(connection_factory=_factory(conn))
    repo.get_pending()

    query, _ = conn.cursor_obj.executed[0]
    assert "EmailSent = 0" in query
    assert "EmailSerialNumber" in query


def test_null_body_becomes_empty_string() -> None:
    rows: list[Row] = [(1, "M", "x@y.com", datetime(2026, 1, 1), "S", None)]
    conn = FakeConnection(rows)
    repo = EmailRepository(connection_factory=_factory(conn))

    email = repo.get_pending()[0]
    assert email.body == ""


def test_mark_sent_uses_serial_number_and_commits() -> None:
    conn = FakeConnection([])
    repo = EmailRepository(connection_factory=_factory(conn))

    repo.mark_sent(16336)

    query, params = conn.cursor_obj.executed[0]
    assert "UPDATE" in query
    assert "EmailSent = 1" in query
    assert "WHERE EmailSerialNumber = ?" in query
    assert params == (16336,)
    assert conn.commits == 1


def test_mark_sent_only_touches_emailsent_column() -> None:
    """Safety property: mark_sent must never write recipient/subject/body.

    We check the SET clause specifically rather than the whole query, because
    a naive substring search would false-positive on the table name itself
    (e.g. "Message" is a substring of "tblEmailMessage").
    """
    conn = FakeConnection([])
    repo = EmailRepository(connection_factory=_factory(conn))
    repo.mark_sent(1)

    query, _ = conn.cursor_obj.executed[0]
    set_clause = query.split("SET", 1)[1].split("WHERE", 1)[0]
    assert "EmailSent" in set_clause
    for forbidden in ("Email_To", "Subject", "Message", "Machine"):
        assert forbidden not in set_clause
