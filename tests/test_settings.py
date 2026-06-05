from pathlib import Path

import pytest

from python_service_template.settings import (
    DEFAULT_APP_NAME,
    DEFAULT_ENV,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RUN_SECONDS,
    ENV_PREFIX,
    Settings,
    load_settings,
)


def test_load_settings_from_valid_toml_file(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text(
        """
[app]
name = "test-service"
log_level = "DEBUG"
env = "TEST"

[service]
run_seconds = 5
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(path)

    assert settings.app_name == "test-service"
    assert settings.log_level == "DEBUG"
    assert settings.env == "TEST"
    assert settings.run_seconds == 5


def test_load_settings_from_missing_toml_file_uses_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.toml")
    assert settings == Settings()  # all defaults


def test_load_settings_with_partial_tables_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text(
        """
[app]
name = "test-service"

[service]
run_seconds = 10
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(path)

    assert settings.app_name == "test-service"
    assert settings.log_level == DEFAULT_LOG_LEVEL
    assert settings.env == DEFAULT_ENV
    assert settings.run_seconds == 10


def test_load_settings_without_app_table_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text(
        """
[service]
run_seconds = 5
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(path)

    assert settings.app_name == DEFAULT_APP_NAME
    assert settings.log_level == DEFAULT_LOG_LEVEL
    assert settings.env == DEFAULT_ENV


def test_load_settings_without_service_table_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text(
        """
[app]
name = "test-service"
log_level = "DEBUG"
env = "TEST"
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(path)

    assert settings.app_name == "test-service"
    assert settings.log_level == "DEBUG"
    assert settings.env == "TEST"
    assert settings.run_seconds == DEFAULT_RUN_SECONDS


def test_load_settings_with_environment_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "app.toml"
    path.write_text(
        """
[app]
name = "test-service"
log_level = "INFO"
env = "dev"

[service]
run_seconds = 1
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv(f"{ENV_PREFIX}_NAME", "env-service")
    monkeypatch.setenv(f"{ENV_PREFIX}_LOG_LEVEL", "WARNING")
    monkeypatch.setenv(f"{ENV_PREFIX}_ENV", "PROD")
    monkeypatch.setenv(f"{ENV_PREFIX}_RUN_SECONDS", "0")

    settings = load_settings(path)

    assert settings.app_name == "env-service"
    assert settings.log_level == "WARNING"
    assert settings.env == "PROD"
    assert settings.run_seconds == 0


def test_settings_raises_for_invalid_log_level() -> None:
    with pytest.raises(ValueError, match="log_level"):
        Settings(log_level="INVALID_LOG_LEVEL")


def test_settings_raises_for_invalid_env() -> None:
    with pytest.raises(ValueError, match="env"):
        Settings(env="INVALID_ENV")


def test_settings_raises_for_negative_run_seconds() -> None:
    with pytest.raises(ValueError, match="run_seconds"):
        Settings(run_seconds=-1)
