from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

import pyodbc

from .settings import Settings

logger = logging.getLogger(__name__)


def build_connection_string(settings: Settings) -> str:
    """Assemble the ODBC connection string from settings.

    Built from a parts list rather than one long f-string so it is easy to
    read and extend. Encrypt and TrustServerCertificate come from settings
    (not hardcoded) so the security posture is visible in config: with ODBC
    Driver 18, Encrypt defaults to "yes" and the driver validates the server
    certificate unless TrustServerCertificate is "yes".
    """
    parts = [
        f"Driver={{{settings.sqlserver_driver}}}",
        f"Server={settings.sqlserver_host}",
        f"Database={settings.sqlserver_database}",
        f"UID={settings.sqlserver_user}",
        f"PWD={settings.sqlserver_password}",
        f"Encrypt={settings.sqlserver_encrypt}",
        f"TrustServerCertificate={settings.sqlserver_trust_cert}",
    ]
    return ";".join(parts) + ";"


@contextmanager
def get_connection(
    settings: Settings,
) -> Generator[pyodbc.Connection, None, None]:  # pragma: no cover
    """Open an authenticated connection and yield it, closing it on exit.

    The connection is guaranteed closed on exit, even if an exception is
    raised inside the with-block. We log the intent to connect BEFORE calling
    pyodbc.connect, so a connection that hangs or fails still leaves a trace.
    The connection string is never logged - it contains the password.
    """
    logger.info(
        "connecting to SQL Server host=%s database=%s user=%s encrypt=%s trust_cert=%s",
        settings.sqlserver_host,
        settings.sqlserver_database,
        settings.sqlserver_user,
        settings.sqlserver_encrypt,
        settings.sqlserver_trust_cert,
    )
    conn = pyodbc.connect(build_connection_string(settings))
    try:
        yield conn
    except pyodbc.Error:
        logger.exception("sqlserver error during connection use")
        raise
    finally:
        conn.close()
        logger.info("sqlserver connection closed")
