from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

import pyodbc

from .settings import Settings

logger = logging.getLogger(__name__)


@contextmanager
def get_connection(settings: Settings) -> Generator[pyodbc.Connection, None, None]:
    """Open an authenticated connection and yield the connection.

    Guarantees the connection is closed on exit, even if an exception is raised inside
    the with-block.
    """
    conn = pyodbc.connect(
        f"Driver={{{settings.sqlserver_driver}}};"
        f"Server={settings.sqlserver_host};"
        f"Database={settings.sqlserver_database};"
        f"UID={settings.sqlserver_user};"
        f"PWD={settings.sqlserver_password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    try:
        logging.info(
            f"connecting to SQL Server {settings.sqlserver_host} database {settings.sqlserver_database} as user {settings.sqlserver_user}"
        )
        yield conn
    except pyodbc.Error as exc:
        logging.error(f"sqlserver connection error: {exc}")
        raise
    finally:
        conn.close()
        logging.info("sqlserver connection closed")
