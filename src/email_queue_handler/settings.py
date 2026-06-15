from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# App
DEFAULT_APP_NAME = "email-queue-handler"
DEFAULT_ENV = "DEV"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "logs/email_queue_handler.log"

# Sql Server
DEFAULT_SQLSERVER_DRIVER = ""
DEFAULT_SQLSERVER_HOST = ""
DEFAULT_SQLSERVER_DATABASE = ""
DEFAULT_SQLSERVER_USER = ""

# Service
DEFAULT_RUN_SECONDS = 1

# Email
DEFAULT_EMAIL_SMTP_SERVER = ""
DEFAULT_EMAIL_SMTP_PORT = 587
DEFAULT_EMAIL_SEND_FROM = ""
DEFAULT_EMAIL_SEND_TO = ""

ENV_PREFIX = "EQH"

VALID_LOG_LEVELS: frozenset[str] = frozenset(logging.getLevelNamesMapping().keys())
VALID_ENVS: frozenset[str] = frozenset({"DEV", "TEST", "PROD"})


@dataclass(frozen=True)
class Settings:
    # App
    app_name: str = DEFAULT_APP_NAME
    env: str = DEFAULT_ENV
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: str = DEFAULT_LOG_FILE

    # SQL Server
    sqlserver_driver: str = DEFAULT_SQLSERVER_DRIVER
    sqlserver_host: str = DEFAULT_SQLSERVER_HOST
    sqlserver_database: str = DEFAULT_SQLSERVER_DATABASE
    sqlserver_user: str = DEFAULT_SQLSERVER_USER
    sqlserver_password: str = ""

    # Service
    run_seconds: int = DEFAULT_RUN_SECONDS

    # Email
    email_smtp_server: str = DEFAULT_EMAIL_SMTP_SERVER
    email_smtp_port: int = DEFAULT_EMAIL_SMTP_PORT
    email_send_from: str = DEFAULT_EMAIL_SEND_FROM
    email_send_to: str = DEFAULT_EMAIL_SEND_TO
    email_password: str = ""

    def __post_init__(self) -> None:
        if self.env not in VALID_ENVS:
            msg = f"env must be one of {VALID_ENVS}, got {self.env}"
            raise ValueError(msg)
        if self.log_level not in VALID_LOG_LEVELS:
            msg = f"log_level must be one of {VALID_LOG_LEVELS}, got {self.log_level}"
            raise ValueError(msg)
        if self.run_seconds < 0:
            msg = f"run_seconds must be >= 0, got {self.run_seconds}"
            raise ValueError(msg)
        if self.email_smtp_port < 1 or self.email_smtp_port > 65535:
            msg = f"email_smtp_port must be between 1 and 65535, got {self.email_smtp_port}"
            raise ValueError(msg)


def _settings_from_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _settings_from_env() -> dict[str, Any]:
    """Collect only env vars that are explicitly set."""
    result: dict[str, Any] = {}
    mapping = {
        # App
        "app_name": f"{ENV_PREFIX}_NAME",
        "env": f"{ENV_PREFIX}_ENV",
        "log_level": f"{ENV_PREFIX}_LOG_LEVEL",
        "log_file": f"{ENV_PREFIX}_LOG_FILE",
        # SQL Server
        "sqlserver_driver": f"{ENV_PREFIX}_SQLSERVER_DRIVER",
        "sqlserver_host": f"{ENV_PREFIX}_SQLSERVER_HOST",
        "sqlserver_database": f"{ENV_PREFIX}_SQLSERVER_DATABASE",
        "sqlserver_user": f"{ENV_PREFIX}_SQLSERVER_USER",
        "sqlserver_password": f"{ENV_PREFIX}_SQLSERVER_PASSWORD",
        # Service
        "run_seconds": f"{ENV_PREFIX}_RUN_SECONDS",
        # Email
        "email_smtp_server": f"{ENV_PREFIX}_EMAIL_SMTP_SERVER",
        "email_smtp_port": f"{ENV_PREFIX}_EMAIL_SMTP_PORT",
        "email_send_from": f"{ENV_PREFIX}_EMAIL_SEND_FROM",
        "email_send_to": f"{ENV_PREFIX}_EMAIL_SEND_TO",
        "email_password": f"{ENV_PREFIX}_EMAIL_PASSWORD",
    }
    for key, env_var in mapping.items():
        value = os.getenv(env_var)
        if value is not None:
            result[key] = value

    return result


def _resolve(env_val: Any, toml_val: Any, default: Any) -> Any:
    """Return the first non-None value in priority order: env > toml > default."""
    if env_val is not None:
        return env_val
    if toml_val is not None:
        return toml_val
    return default


def load_settings(path: Path) -> Settings:
    toml_data = _settings_from_toml(path)
    toml_app = toml_data.get("app", {})
    toml_sql = toml_data.get("sqlserver", {})
    toml_svc = toml_data.get("service", {})
    toml_email = toml_data.get("email", {})
    env_data = _settings_from_env()

    return Settings(
        # App
        app_name=str(_resolve(env_data.get("app_name"), toml_app.get("name"), DEFAULT_APP_NAME)),
        env=str(_resolve(env_data.get("env"), toml_app.get("env"), DEFAULT_ENV)).upper(),
        log_level=str(
            _resolve(env_data.get("log_level"), toml_app.get("log_level"), DEFAULT_LOG_LEVEL)
        ).upper(),
        log_file=str(
            _resolve(env_data.get("log_file"), toml_app.get("log_file"), DEFAULT_LOG_FILE)
        ),
        # SQL Server
        sqlserver_driver=str(
            _resolve(
                env_data.get("sqlserver_driver"), toml_sql.get("driver"), DEFAULT_SQLSERVER_DRIVER
            )
        ),
        sqlserver_host=str(
            _resolve(env_data.get("sqlserver_host"), toml_sql.get("host"), DEFAULT_SQLSERVER_HOST)
        ),
        sqlserver_database=str(
            _resolve(
                env_data.get("sqlserver_database"),
                toml_sql.get("database"),
                DEFAULT_SQLSERVER_DATABASE,
            )
        ),
        sqlserver_user=str(
            _resolve(env_data.get("sqlserver_user"), toml_sql.get("user"), DEFAULT_SQLSERVER_USER)
        ),
        sqlserver_password=str(_resolve(env_data.get("sqlserver_password"), None, "")),
        # Service
        run_seconds=int(
            _resolve(env_data.get("run_seconds"), toml_svc.get("run_seconds"), DEFAULT_RUN_SECONDS)
        ),
        # Email
        email_smtp_server=str(
            _resolve(
                env_data.get("email_smtp_server"),
                toml_email.get("smtp_server"),
                DEFAULT_EMAIL_SMTP_SERVER,
            )
        ),
        email_smtp_port=int(
            _resolve(
                env_data.get("email_smtp_port"),
                toml_email.get("smtp_port"),
                DEFAULT_EMAIL_SMTP_PORT,
            )
        ),
        email_send_from=str(
            _resolve(
                env_data.get("email_send_from"),
                toml_email.get("send_from"),
                DEFAULT_EMAIL_SEND_FROM,
            )
        ),
        email_send_to=str(
            _resolve(
                env_data.get("email_send_to"),
                toml_email.get("send_to"),
                DEFAULT_EMAIL_SEND_TO,
            )
        ),
        email_password=str(_resolve(env_data.get("email_password"), None, "")),
    )
