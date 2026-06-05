from pathlib import Path

from python_service_template.config import resolve_settings
from python_service_template.settings import DEFAULT_APP_NAME


def test_resolve_settings_with_no_path_uses_default() -> None:
    # No config file exists at the default path in the test environment,
    # so we expect defaults to be returned without raising.
    settings = resolve_settings(Path("nonexistent_config_for_testing.toml"))
    assert settings.app_name == DEFAULT_APP_NAME
    assert settings.log_level == "INFO"
    assert settings.env == "DEV"
    assert settings.run_seconds == 1


def test_resolve_settings_with_explicit_path(tmp_path: Path) -> None:
    path = tmp_path / "app.toml"
    path.write_text(
        """
[app]
name = "config-test-app"
log_level = "DEBUG"
env = "DEV"

[service]
run_seconds = 3
""".strip(),
        encoding="utf-8",
    )

    settings = resolve_settings(path)

    assert settings.app_name == "config-test-app"
    assert settings.log_level == "DEBUG"
    assert settings.env == "DEV"
    assert settings.run_seconds == 3
