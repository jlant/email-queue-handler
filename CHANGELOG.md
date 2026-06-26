# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-26

First release. Monitors a SQL Server queue and dispatches pending emails via
SMTP, designed to run as a Windows Scheduled Task once per minute.

### Added
- Queue processing: reads `dbo.tblEmailMessage` rows where `EmailSent = 0`,
  sends each via SMTP, and marks sent rows by `EmailSerialNumber`.
- Send-then-mark ordering: a row is marked sent only after the email is sent,
  so a mid-run failure causes a recoverable duplicate rather than a lost email.
- Per-email resilience: each message is processed in isolation; a bad recipient
  is logged and skipped without halting the queue.
- Run-level failure alerts: an administrator is emailed if the database or SMTP
  server is unreachable.
- Repository pattern over the SQL boundary, with `EmailMailer` / `EmailMarker`
  Protocols isolating business logic from `pyodbc` and `smtplib`.
- Settings resolution (environment variable > `config/app.toml` > default) with
  fail-fast validation when `env = "PROD"`. Secrets are supplied only via
  `EQH_SQLSERVER_PASSWORD` and `EQH_EMAIL_PASSWORD`.
- Explicit `encrypt` / `trust_cert` settings for ODBC Driver 18 connections.
- Typer CLI: `run`, `read-config` (prints resolved settings with passwords
  masked), and `--version`.
- Console + rotating-file logging.
- Test suite (pytest) using in-memory fakes, with strict pyright type checking
  and ruff lint/format, orchestrated by nox across Python 3.11 and 3.12.
- Windows deployment scripts (`scripts/`): machine-wide uv install,
  least-privilege service account with batch-logon right, machine-scoped
  secrets, scheduled-task registration, a deploy/update script
  (`git pull` + `uv sync --frozen` + test gate), and a smoke test.

### Known limitations
- No poison-message handling: a permanently-unsendable email stays
  `EmailSent = 0` and is retried every run.

[Unreleased]: https://github.com/jlant/email-queue-handler/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jlant/email-queue-handler/releases/tag/v0.1.0
