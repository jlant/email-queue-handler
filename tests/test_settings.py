"""Tests for settings resolution and validation.

Pure logic - no fakes needed. Covers the resolution precedence
(env > toml > default), the new encrypt/trust_cert fields, and the
fail-fast PROD validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from email_queue_handler.settings import Settings, load_settings


class TestDefaults:
    def test_driver18_secure_defaults(self) -> None:
        s = Settings()
        assert s.sqlserver_encrypt == "yes"
        assert s.sqlserver_trust_cert == "no"  # secure default: opt in to trust

    def test_default_env_is_dev(self) -> None:
        assert Settings().env == "DEV"


class TestValidation:
    def test_invalid_env_rejected(self) -> None:
        with pytest.raises(ValueError, match="env must be one of"):
            Settings(env="STAGING")

    def test_invalid_log_level_rejected(self) -> None:
        with pytest.raises(ValueError, match="log_level must be one of"):
            Settings(log_level="CHATTY")

    def test_out_of_range_port_rejected(self) -> None:
        with pytest.raises(ValueError, match="email_smtp_port"):
            Settings(email_smtp_port=70000)

    def test_invalid_encrypt_value_rejected(self) -> None:
        with pytest.raises(ValueError, match="sqlserver_encrypt"):
            Settings(sqlserver_encrypt="maybe")


class TestProdValidation:
    def test_prod_with_missing_fields_fails_fast(self) -> None:
        with pytest.raises(ValueError, match="required in PROD"):
            Settings(env="PROD")

    def test_prod_error_names_the_missing_fields(self) -> None:
        with pytest.raises(ValueError) as exc:
            Settings(env="PROD", sqlserver_host="h")  # still missing others
        msg = str(exc.value)
        assert "sqlserver_driver" in msg
        assert "sqlserver_host" not in msg  # this one WAS provided

    def test_fully_configured_prod_is_valid(self) -> None:
        s = Settings(
            env="PROD",
            sqlserver_driver="ODBC Driver 18 for SQL Server",
            sqlserver_host="sql01",
            sqlserver_database="db",
            sqlserver_user="u",
            sqlserver_password="pw",
            email_smtp_server="smtp",
            email_send_from="f@x",
            email_password="pw2",
        )
        assert s.env == "PROD"

    def test_dev_stays_lenient(self) -> None:
        # DEV with everything blank must NOT raise - local experimentation.
        Settings(env="DEV")


class TestResolution:
    def test_toml_values_load(self, tmp_path: Path) -> None:
        cfg = tmp_path / "app.toml"
        cfg.write_text(
            '[app]\nenv = "DEV"\n[sqlserver]\nhost = "sql99"\ntrust_cert = "yes"\n',
            encoding="utf-8",
        )
        s = load_settings(cfg)
        assert s.sqlserver_host == "sql99"
        assert s.sqlserver_trust_cert == "yes"

    def test_env_overrides_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = tmp_path / "app.toml"
        cfg.write_text('[sqlserver]\nhost = "from_toml"\n', encoding="utf-8")
        monkeypatch.setenv("EQH_SQLSERVER_HOST", "from_env")
        s = load_settings(cfg)
        assert s.sqlserver_host == "from_env"

    def test_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        s = load_settings(tmp_path / "does_not_exist.toml")
        assert s.app_name == "email-queue-handler"
