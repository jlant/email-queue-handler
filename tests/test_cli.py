"""Tests for the CLI surface.

We use Typer's CliRunner to invoke commands as a user would. The run command
is exercised against an empty queue (repository monkeypatched to return no
pending emails) so it proves the CLI wiring and exit codes without any real
database or SMTP I/O.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.conftest import FakeMailer, FakeRepository
from typer.testing import CliRunner

import email_queue_handler.service as service_mod
from email_queue_handler.cli import CLI_NAME, app

runner = CliRunner()


def test_version_flag() -> None:
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert CLI_NAME in r.stdout


def test_read_config_missing_file(tmp_path: Path) -> None:
    """A non-existent config path falls back to defaults gracefully."""
    missing = tmp_path / "missing.toml"
    r = runner.invoke(app, ["read-config", "--config", str(missing)])
    assert r.exit_code == 0
    assert "app_name=" in r.stdout
    assert "log_level=" in r.stdout


def test_read_config_with_file(tmp_path: Path) -> None:
    config = tmp_path / "app.toml"
    config.write_text(
        """
[app]
name = "cli-test-app"
log_level = "WARNING"
env = "TEST"
""".strip(),
        encoding="utf-8",
    )
    r = runner.invoke(app, ["read-config", "--config", str(config)])
    assert r.exit_code == 0
    assert "cli-test-app" in r.stdout
    assert "WARNING" in r.stdout


def test_read_config_masks_secrets(tmp_path: Path) -> None:
    """read-config must never print a password value, only whether it is set."""
    config = tmp_path / "app.toml"
    config.write_text('[app]\nenv = "TEST"\n', encoding="utf-8")
    r = runner.invoke(
        app,
        ["read-config", "--config", str(config)],
        env={"EQH_EMAIL_PASSWORD": "super-secret-value"},
    )
    assert r.exit_code == 0
    assert "super-secret-value" not in r.stdout


def test_run_command_empty_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A run against an empty queue exits 0 and touches no real I/O."""
    config = tmp_path / "app.toml"
    config.write_text(
        """
[app]
name = "run-test"
log_level = "INFO"
env = "TEST"
""".strip(),
        encoding="utf-8",
    )

    empty_repo = FakeRepository(pending=[])

    def fake_repo(connection_factory: object) -> FakeRepository:
        return empty_repo

    def fake_mailer(**kwargs: object) -> FakeMailer:
        return FakeMailer()

    monkeypatch.setattr(service_mod, "EmailRepository", fake_repo)
    monkeypatch.setattr(service_mod, "SmtpMailer", fake_mailer)

    r = runner.invoke(app, ["run", "--config", str(config)])
    assert r.exit_code == 0
