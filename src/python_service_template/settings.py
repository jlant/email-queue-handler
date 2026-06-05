from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_APP_NAME = "python-service-template"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_ENV = "DEV"
DEFAULT_RUN_SECONDS = 1

ENV_PREFIX = "APP"

VALID_LOG_LEVELS: frozenset[str] = frozenset(logging.getLevelNamesMapping().keys())
VALID_ENVS: frozenset[str] = frozenset({"DEV", "TEST", "PROD"})


@dataclass(frozen=True)
class Settings:
    app_name: str = DEFAULT_APP_NAME
    log_level: str = DEFAULT_LOG_LEVEL
    env: str = DEFAULT_ENV
    run_seconds: int = DEFAULT_RUN_SECONDS

    def __post_init__(self) -> None:
        if self.log_level not in VALID_LOG_LEVELS:
            msg = f"log_level must be one of {VALID_LOG_LEVELS}, got {self.log_level}"
            raise ValueError(msg)
        if self.env not in VALID_ENVS:
            msg = f"env must be one of {VALID_ENVS}, got {self.env}"
            raise ValueError(msg)
        if self.run_seconds < 0:
            msg = f"run_seconds must be >= 0, got {self.run_seconds}"
            raise ValueError(msg)


def _settings_from_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _settings_from_env() -> dict[str, Any]:
    """Collect only env vars that are explicitly set."""
    result: dict[str, Any] = {}
    mapping = {
        "app_name": f"{ENV_PREFIX}_NAME",
        "log_level": f"{ENV_PREFIX}_LOG_LEVEL",
        "env": f"{ENV_PREFIX}_ENV",
        "run_seconds": f"{ENV_PREFIX}_RUN_SECONDS",
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
    toml_svc = toml_data.get("service", {})
    env_data = _settings_from_env()

    return Settings(
        app_name=str(_resolve(env_data.get("app_name"), toml_app.get("name"), DEFAULT_APP_NAME)),
        log_level=str(
            _resolve(env_data.get("log_level"), toml_app.get("log_level"), DEFAULT_LOG_LEVEL)
        ).upper(),
        env=str(_resolve(env_data.get("env"), toml_app.get("env"), DEFAULT_ENV)).upper(),
        run_seconds=int(
            _resolve(env_data.get("run_seconds"), toml_svc.get("run_seconds"), DEFAULT_RUN_SECONDS)
        ),
    )
