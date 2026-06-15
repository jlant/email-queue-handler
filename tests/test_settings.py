from pathlib import Path

import pytest

from email_queue_handler.settings import (
    DEFAULT_APP_NAME,
    DEFAULT_EMAIL_SMTP_PORT,
    DEFAULT_ENV,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RUN_SECONDS,
    ENV_PREFIX,
    Settings,
    load_settings,
)

# --- Settings dataclass validation ---


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.app_name == DEFAULT_APP_NAME
    assert settings.env == DEFAULT_ENV
    assert settings.log_level == DEFAULT_LOG_LEVEL
    assert settings.log_file == DEFAULT_LOG_FILE
    assert settings.run_seconds == DEFAULT_RUN_SECONDS
    assert settings.email_smtp_port == DEFAULT_EMAIL_SMTP_PORT
    assert settings.sqlserver_password == ""
    assert settings.email_password == ""


def test_settings_rejects_invalid_log_level() -> None:
    with pytest.raises(ValueError, match="log_level"):
        Settings(log_level="VERBOSE")


def test_settings_rejects_invalid_env() -> None:
    with pytest.raises(ValueError, match="env"):
        Settings(env="STAGING")


def test_settings_rejects_negative_run_seconds() -> None:
    with pytest.raises(ValueError, match="run_seconds"):
        Settings(run_seconds=-1)


def test_settings_rejects_invalid_email_smtp_port() -> None:
    with pytest.raises(ValueError, match="email_smtp_port"):
        Settings(email_smtp_port=0)


# --- load_settings from TOML ---


def test_load_settings_from_missing_toml_file_uses_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.toml")
    assert settings == Settings()  # all defaults


def test_load_settings_from_valid_toml_file(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text(
        """
[app]
name = "test-handler"
env = "TEST"
log_level = "DEBUG"
log_file = "/logs/test_handler.log"

[sqlserver]
driver = "sql_odbc_driver"
host = "10.0.0.1"
database = "sql_database"
user = "sql_user"

[service]
run_seconds = 0

[email]
smtp_server = "mail.example.com"
smtp_port = 587
send_from = "from@example.com"
send_to = "to@example.com"
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(path)

    assert settings.app_name == "test-handler"
    assert settings.env == "TEST"
    assert settings.log_level == "DEBUG"
    assert settings.log_file == "/logs/test_handler.log"
    assert settings.sqlserver_driver == "sql_odbc_driver"
    assert settings.sqlserver_host == "10.0.0.1"
    assert settings.sqlserver_database == "sql_database"
    assert settings.sqlserver_user == "sql_user"
    assert settings.sqlserver_password == ""  # never from TOML
    assert settings.run_seconds == 0
    assert settings.email_smtp_server == "mail.example.com"
    assert settings.email_smtp_port == 587
    assert settings.email_send_from == "from@example.com"
    assert settings.email_send_to == "to@example.com"
    assert settings.email_password == ""  # never from TOML


def test_load_settings_with_missing_tables_uses_default(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text('[app]\nname = "partial-config"\n', encoding="utf-8")
    settings = load_settings(path)
    assert settings.app_name == "partial-config"
    assert settings.sqlserver_host == ""
    assert settings.log_level == DEFAULT_LOG_LEVEL


# --- load_settings env var overrides ---


def test_load_settings_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "app.toml"
    path.write_text('[app]\nlog_level = "INFO"\n', encoding="utf-8")
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_LEVEL", "WARNING")

    settings = load_settings(path)

    assert settings.log_level == "WARNING"


def test_load_settings_sqlserver_password_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_SQLSERVER_PASSWORD", "secret123")
    settings = load_settings(tmp_path / "missing.toml")
    assert settings.sqlserver_password == "secret123"


def test_load_settings_email_password_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}_EMAIL_PASSWORD", "emailsecret")
    settings = load_settings(tmp_path / "missing.toml")
    assert settings.email_password == "emailsecret"


def test_load_settings_passwords_not_loaded_from_toml(tmp_path: Path) -> None:
    # Even if someone mistakenly adds passwords to the TOML, they must not be loaded.
    # Passwords only come from env vars — this is enforced in load_settings().
    path = tmp_path / "app.toml"
    path.write_text('[sftp]\nhost = "10.0.0.1"\n', encoding="utf-8")
    settings = load_settings(path)
    assert settings.sqlserver_password == ""
    assert settings.email_password == ""
