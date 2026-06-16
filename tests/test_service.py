"""Tests for the service orchestration layer.

We inject the fakes by monkeypatching the two things the service constructs
internally: the connection factory (via EmailRepository) and the SmtpMailer.
This proves the loop, the duplicate-safety across a batch, and the two
distinct failure paths - all without real I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any, TypeAlias

import pytest
from tests.conftest import FakeMailer, FakeRepository, make_email

import email_queue_handler.service as service_mod
from email_queue_handler.service import Service
from email_queue_handler.settings import Settings

if TYPE_CHECKING:
    import pyodbc

# String forward reference so pyodbc is only needed by the type checker, not at
# runtime. These unit tests use fakes and never load the real ODBC driver.
ConnFactory: TypeAlias = "Callable[[], AbstractContextManager[pyodbc.Connection]]"


def _settings() -> Settings:
    return Settings(
        env="DEV",
        email_smtp_server="smtp.test",
        email_send_from="from@test",
        email_send_to="admin@test",
        email_password="x",
    )


def _wire(monkeypatch: pytest.MonkeyPatch, repo: FakeRepository, mailer: FakeMailer) -> None:
    """Point the service at our fakes."""

    def fake_repo(connection_factory: ConnFactory) -> FakeRepository:
        return repo

    def fake_mailer(**kwargs: Any) -> FakeMailer:
        return mailer

    monkeypatch.setattr(service_mod, "EmailRepository", fake_repo)
    monkeypatch.setattr(service_mod, "SmtpMailer", fake_mailer)


def test_clean_run_sends_all_and_marks_all(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeRepository(pending=[make_email(1), make_email(2), make_email(3)])
    mailer = FakeMailer()
    _wire(monkeypatch, repo, mailer)

    svc = Service(_settings())
    svc.start()
    summary = svc.run()

    assert summary.fetched == 3
    assert summary.sent == 3
    assert summary.failed == 0
    assert summary.run_failed is False
    assert repo.marked == [1, 2, 3]


def test_one_bad_email_does_not_halt_the_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    """The middle email is bad. The other two must still send and be marked,
    and the run is NOT considered failed."""
    repo = FakeRepository(pending=[make_email(1), make_email(2, "bad@x.com"), make_email(3)])
    mailer = FakeMailer(fail_recipients={"bad@x.com"})
    _wire(monkeypatch, repo, mailer)

    svc = Service(_settings())
    svc.start()
    summary = svc.run()

    assert summary.fetched == 3
    assert summary.sent == 2
    assert summary.failed == 1
    assert summary.run_failed is False
    assert repo.marked == [1, 3]


def test_empty_queue_is_a_clean_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeRepository(pending=[])
    mailer = FakeMailer()
    _wire(monkeypatch, repo, mailer)

    svc = Service(_settings())
    svc.start()
    summary = svc.run()

    assert summary.fetched == 0
    assert summary.sent == 0
    assert summary.run_failed is False
    assert mailer.opened is False


def test_database_unreachable_is_a_run_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeRepository(fail_on_fetch=True)
    mailer = FakeMailer()
    _wire(monkeypatch, repo, mailer)

    alerts: list[str] = []

    def fake_alert(self: Service, msg: str) -> None:
        alerts.append(msg)

    monkeypatch.setattr(Service, "_alert", fake_alert)

    svc = Service(_settings())
    svc.start()
    summary = svc.run()

    assert summary.run_failed is True
    assert len(alerts) == 1
    assert "read email queue" in alerts[0]


def test_smtp_unreachable_is_a_run_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeRepository(pending=[make_email(1)])
    mailer = FakeMailer(fail_on_open=True)
    _wire(monkeypatch, repo, mailer)

    alerts: list[str] = []

    def fake_alert(self: Service, msg: str) -> None:
        alerts.append(msg)

    monkeypatch.setattr(Service, "_alert", fake_alert)

    svc = Service(_settings())
    svc.start()
    summary = svc.run()

    assert summary.run_failed is True
    assert repo.marked == []
    assert len(alerts) == 1
    assert "SMTP" in alerts[0]


def test_run_before_start_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeRepository(pending=[])
    mailer = FakeMailer()
    _wire(monkeypatch, repo, mailer)

    svc = Service(_settings())
    with pytest.raises(RuntimeError, match="must be started"):
        svc.run()
