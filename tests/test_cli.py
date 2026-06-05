from pathlib import Path

from typer.testing import CliRunner

from python_service_template.cli import CLI_NAME, app

runner = CliRunner()


def test_hello_default_name() -> None:
    r = runner.invoke(app, ["hello"])
    assert r.exit_code == 0
    assert "Hello, world" in r.stdout


def test_hello_custom_name() -> None:
    r = runner.invoke(app, ["hello", "--name", "Jeremiah"])
    assert r.exit_code == 0
    assert "Hello, Jeremiah" in r.stdout


def test_version_flag() -> None:
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    # Should print the CLI name and a version string
    assert CLI_NAME in r.stdout


def test_read_config_missing_file(tmp_path: Path) -> None:
    # A non-existent config path falls back to defaults gracefully
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
env = "PROD"

[service]
run_seconds = 0
""".strip(),
        encoding="utf-8",
    )
    r = runner.invoke(app, ["read-config", "--config", str(config)])
    assert r.exit_code == 0
    assert "cli-test-app" in r.stdout
    assert "WARNING" in r.stdout


def test_run_command(tmp_path: Path) -> None:
    config = tmp_path / "app.toml"
    config.write_text(
        """
[app]
name = "run-test"
log_level = "INFO"
env = "TEST"

[service]
run_seconds = 0
""".strip(),
        encoding="utf-8",
    )
    r = runner.invoke(app, ["run", "--config", str(config)])
    assert r.exit_code == 0
