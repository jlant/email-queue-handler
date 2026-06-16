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

# SQL Server
DEFAULT_SQLSERVER_DRIVER = ""
DEFAULT_SQLSERVER_HOST = ""
DEFAULT_SQLSERVER_DATABASE = ""
DEFAULT_SQLSERVER_USER = ""
# ODBC Driver 18 defaults Encrypt to "yes"; we make it explicit. TrustServer
# Certificate defaults to "no" - the SECURE default. Trusting a self-signed
# cert is something you opt into deliberately, per environment, never by
# accident buried in a connection string.
DEFAULT_SQLSERVER_ENCRYPT = "yes"
DEFAULT_SQLSERVER_TRUST_CERT = "no"

# Email
DEFAULT_EMAIL_SMTP_SERVER = ""
DEFAULT_EMAIL_SMTP_PORT = 587
DEFAULT_EMAIL_SEND_FROM = ""
DEFAULT_EMAIL_SEND_TO = ""

ENV_PREFIX = "EQH"

VALID_LOG_LEVELS: frozenset[str] = frozenset(logging.getLevelNamesMapping().keys())
VALID_ENVS: frozenset[str] = frozenset({"DEV", "TEST", "PROD"})
VALID_YES_NO: frozenset[str] = frozenset({"yes", "no"})

# Fields that must be non-empty when running in PROD. Misconfiguring any of
# these should fail loudly at startup with a clear message, not deep inside a
# pyodbc/smtplib call with a cryptic driver error.
REQUIRED_IN_PROD: tuple[str, ...] = (
    "sqlserver_driver",
    "sqlserver_host",
    "sqlserver_database",
    "sqlserver_user",
    "sqlserver_password",
    "email_smtp_server",
    "email_send_from",
    "email_password",
)


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
    sqlserver_encrypt: str = DEFAULT_SQLSERVER_ENCRYPT
    sqlserver_trust_cert: str = DEFAULT_SQLSERVER_TRUST_CERT

    # Email
    email_smtp_server: str = DEFAULT_EMAIL_SMTP_SERVER
    email_smtp_port: int = DEFAULT_EMAIL_SMTP_PORT
    email_send_from: str = DEFAULT_EMAIL_SEND_FROM
    email_send_to: str = DEFAULT_EMAIL_SEND_TO
    email_password: str = ""

    def __post_init__(self) -> None:
        if self.env not in VALID_ENVS:
            msg = f"env must be one of {sorted(VALID_ENVS)}, got {self.env!r}"
            raise ValueError(msg)
        if self.log_level not in VALID_LOG_LEVELS:
            msg = f"log_level must be one of {sorted(VALID_LOG_LEVELS)}, got {self.log_level!r}"
            raise ValueError(msg)
        if self.email_smtp_port < 1 or self.email_smtp_port > 65535:
            msg = f"email_smtp_port must be between 1 and 65535, got {self.email_smtp_port}"
            raise ValueError(msg)
        if self.sqlserver_encrypt not in VALID_YES_NO:
            msg = f"sqlserver_encrypt must be 'yes' or 'no', got {self.sqlserver_encrypt!r}"
            raise ValueError(msg)
        if self.sqlserver_trust_cert not in VALID_YES_NO:
            msg = f"sqlserver_trust_cert must be 'yes' or 'no', got {self.sqlserver_trust_cert!r}"
            raise ValueError(msg)

        # Fail fast in PROD if any required connection field is blank.
        if self.env == "PROD":
            missing = [name for name in REQUIRED_IN_PROD if not getattr(self, name).strip()]
            if missing:
                msg = (
                    "the following settings are required in PROD but are empty: "
                    f"{', '.join(missing)}"
                )
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
        "sqlserver_encrypt": f"{ENV_PREFIX}_SQLSERVER_ENCRYPT",
        "sqlserver_trust_cert": f"{ENV_PREFIX}_SQLSERVER_TRUST_CERT",
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
        sqlserver_encrypt=str(
            _resolve(
                env_data.get("sqlserver_encrypt"),
                toml_sql.get("encrypt"),
                DEFAULT_SQLSERVER_ENCRYPT,
            )
        ).lower(),
        sqlserver_trust_cert=str(
            _resolve(
                env_data.get("sqlserver_trust_cert"),
                toml_sql.get("trust_cert"),
                DEFAULT_SQLSERVER_TRUST_CERT,
            )
        ).lower(),
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
