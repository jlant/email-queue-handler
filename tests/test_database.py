"""Tests for the database boundary's pure logic.

We test build_connection_string because it is pure logic - it assembles a
string from settings with no I/O - and a bug in it (wrong field, missing
separator, wrong encrypt value) would be a real defect. We do NOT test
get_connection itself, because that calls pyodbc.connect against a real
server; that path is exercised by integration testing and live deployment
verification, not unit tests, and is marked with `# pragma: no cover`.
"""

from __future__ import annotations

from email_queue_handler.database import build_connection_string
from email_queue_handler.settings import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "sqlserver_driver": "ODBC Driver 18 for SQL Server",
        "sqlserver_host": "SQL01",
        "sqlserver_database": "OracleInterface",
        "sqlserver_user": "svc_eqh",
        "sqlserver_password": "secret",
        "sqlserver_encrypt": "yes",
        "sqlserver_trust_cert": "no",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_connection_string_includes_all_parts() -> None:
    cs = build_connection_string(_settings())
    assert "Driver={ODBC Driver 18 for SQL Server}" in cs
    assert "Server=SQL01" in cs
    assert "Database=OracleInterface" in cs
    assert "UID=svc_eqh" in cs
    assert "PWD=secret" in cs
    assert "Encrypt=yes" in cs
    assert "TrustServerCertificate=no" in cs


def test_connection_string_reflects_trust_cert_setting() -> None:
    cs = build_connection_string(_settings(sqlserver_trust_cert="yes"))
    assert "TrustServerCertificate=yes" in cs


def test_connection_string_is_semicolon_terminated() -> None:
    cs = build_connection_string(_settings())
    assert cs.endswith(";")
    # Each part is separated; there should be no doubled separators.
    assert ";;" not in cs
