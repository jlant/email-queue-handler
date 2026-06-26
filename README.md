# Email Queue Handler

An automated Python service that monitors a SQL Server database queue,
dispatches pending emails via SMTP, and records delivery status. It is designed
to run as a Windows Scheduled Task once per minute: each invocation processes
the queue once and exits.

## What it does

A SQL Server table (`OracleInterface` database, `dbo.tblEmailMessage`) holds
email messages produced by other systems. Each row has an `EmailSent` flag.
On every run, the handler:

1. Reads all rows where `EmailSent = 0`.
2. Sends each one via SMTP, individually.
3. Marks each successfully-sent row `EmailSent = 1`, using its unique
   `EmailSerialNumber`.

The design favors correctness and resilience over throughput:

- **Send, then mark — never the reverse.** A row is marked sent only *after*
  the email is actually sent. If the process dies in between, the email is
  re-sent next run (a duplicate, which is recoverable) rather than silently
  lost. This ordering is the system's core correctness property.
- **One bad email never halts the queue.** Each message is processed in
  isolation; a bad recipient is logged and skipped, and the rest still send.
- **Run-level failures alert an administrator.** If the database or SMTP server
  is unreachable, the run fails fast, logs loudly, and emails the configured
  admin address.

## Architecture

The code separates business logic from the two external boundaries (the
database and SMTP) so the logic can be tested without either.

| Module | Responsibility |
|---|---|
| `cli.py` | Typer CLI: `run`, `read-config`, `--version`. |
| `service.py` | Orchestrates one run: fetch, loop, summarize, alert on run-level failure. |
| `processor.py` | The per-email business rule (validate → send → mark). |
| `protocols.py` | `EmailMailer` / `EmailMarker` interfaces the processor depends on. |
| `email_repository.py` | The SQL boundary: reads pending, marks sent. |
| `base_repository.py` | Shared repository plumbing (connection factory). |
| `database.py` | Opens/closes the pyodbc connection; builds the connection string. |
| `mailer.py` | The SMTP boundary: `SmtpMailer` + the failure-alert sender. |
| `models.py` | `Email` and `EmailResult` data classes. |
| `settings.py` | Settings resolution (env > TOML > default) and validation. |
| `config.py` | Thin `resolve_settings()` entry point. |
| `logging.py` | Configures console + rotating-file logging. |

Because `processor.py` and `service.py` depend on the `EmailMailer` and
`EmailMarker` Protocols rather than on `pyodbc`/`smtplib` directly, the test
suite substitutes in-memory fakes and exercises the full send-then-mark loop
with no network or database.

## Configuration

Settings resolve in priority order: **environment variable > `config/app.toml`
> built-in default**. Environment variables use the prefix `EQH_` and the
pattern `EQH_<SECTION>_<KEY>` (e.g. `EQH_SQLSERVER_HOST`).

Non-secret settings live in `config/app.toml`. **Secrets (passwords) are never
committed** — they are supplied via machine-scoped environment variables:

- `EQH_SQLSERVER_PASSWORD`
- `EQH_EMAIL_PASSWORD`

Setting `env = "PROD"` enables fail-fast validation: every required connection
field (and both password env vars) must be non-empty, or the service raises a
clear error at startup naming what is missing.

The `read-config` command prints the resolved settings with passwords masked,
which is the quickest way to confirm a deployment is configured correctly.

## Local development

Requires Python >= 3.11 and [uv](https://docs.astral.sh/uv/). On Linux, `pyodbc`
needs the unixODBC system library (`sudo apt-get install unixodbc`); on Windows
it needs the matching ODBC driver (e.g. *ODBC Driver 18 for SQL Server*).

```bash
uv sync                 # build the locked virtual environment
uv run eqh --version    # confirm the CLI works
uv run eqh read-config  # print resolved settings (passwords masked)
uv run eqh run          # run one pass over the queue
```

### Quality checks

The project uses ruff (lint + format), pyright (strict type checking), and
pytest (with a coverage gate), orchestrated by nox:

```bash
uv run nox -s lint      # ruff + pyright on Python 3.11 and 3.12
uv run nox -s tests     # pytest with coverage (fails under 80%)
uv run nox              # everything
```

## Deployment (Windows Server)

Deployment is built on git + uv, with no packaging step. The `scripts/`
directory contains numbered PowerShell scripts that take a bare server to a
running task. Run them elevated; on a fresh server they are run in order.

> Scripts are unsigned. Run each as
> `powershell -ExecutionPolicy Bypass -File .\<script>.ps1`.

| Script | Purpose | When |
|---|---|---|
| `00_install_uv_machine_wide.ps1` | Install uv under `C:\ProgramData\uv` so the service account can use it. | Once per server. |
| `01_create_service_account.ps1` | Create the least-privilege `svc_eqh` account and grant it "Log on as a batch job". | Once per server. |
| `02_set_machine_env.ps1` | Set the two secret env vars at machine scope. | Once (re-run to rotate secrets). |
| `05_deploy.ps1` | `git pull` + `uv sync --frozen` + test gate + log-dir permissions. | Every deploy/update. |
| `03_register_task.ps1` | Register the every-minute scheduled task as `svc_eqh`. | Once per server. |
| `04_smoke_test.ps1` | Verify uv, config, a forced run, and the log tail. | After every deploy. |
| `06_control.ps1` | Check status, pause/resume, stop, or trigger the task. | As needed (operational). |

### First install

```powershell
git clone https://github.com/jlant/email-queue-handler.git C:\Apps\email-queue-handler
cd C:\Apps\email-queue-handler\scripts
powershell -ExecutionPolicy Bypass -File .\00_install_uv_machine_wide.ps1
powershell -ExecutionPolicy Bypass -File .\01_create_service_account.ps1
powershell -ExecutionPolicy Bypass -File .\05_deploy.ps1 -NoPull
powershell -ExecutionPolicy Bypass -File .\02_set_machine_env.ps1
powershell -ExecutionPolicy Bypass -File .\03_register_task.ps1
powershell -ExecutionPolicy Bypass -File .\04_smoke_test.ps1
```

Fill in the real non-secret values in `config\app.toml` (SQL host, database,
user; SMTP server, addresses) before the smoke test.

### Updating to a new version

The task keeps pointing at `uv run eqh run`, so an update is just new code:

```powershell
cd C:\Apps\email-queue-handler\scripts
powershell -ExecutionPolicy Bypass -File .\05_deploy.ps1      # pull + sync + test
powershell -ExecutionPolicy Bypass -File .\04_smoke_test.ps1  # confirm new code runs
```

No need to re-register the task or touch the service account. If a deploy's
test gate fails, the previous code is left in place and the task keeps running
it.

### Rollback

Because `uv.lock` is committed alongside the code, checking out an earlier
commit restores that version's exact dependencies too:

```powershell
git checkout <previous-tag-or-commit>
powershell -ExecutionPolicy Bypass -File .\05_deploy.ps1 -NoPull
```

### Operating the service (start / stop / status)

Use `06_control.ps1` to control the running task. With no switch it shows
status only (read-only).

```powershell
cd C:\Apps\email-queue-handler\scripts

# Check status (state, last result, next run) — read-only
powershell -ExecutionPolicy Bypass -File .\06_control.ps1

# Pause (reversible) — stops the task from firing
powershell -ExecutionPolicy Bypass -File .\06_control.ps1 -Disable

# Resume
powershell -ExecutionPolicy Bypass -File .\06_control.ps1 -Enable

# Stop an in-flight run AND pause
powershell -ExecutionPolicy Bypass -File .\06_control.ps1 -Disable -StopRunning

# Trigger one run now (without changing enabled/disabled state)
powershell -ExecutionPolicy Bypass -File .\06_control.ps1 -RunNow
```

Pausing is lossless: while the task is disabled, rows accumulate in the queue
with `EmailSent = 0` and are sent when it is re-enabled. To remove the task
entirely (decommissioning), unregister it:

```powershell
Unregister-ScheduledTask -TaskName "EmailQueueHandler" -Confirm:$false
```

## How it runs in production

A Windows Scheduled Task triggers `uv run eqh run` every minute as the
`svc_eqh` service account, configured to not start a new instance if the
previous one is still running (no overlap) and with a 5-minute execution limit
(a hung run is killed; the next minute starts fresh). The scheduler is the
loop — the service itself does one pass and exits. Output goes to a rotating
log at `logs/email_queue_handler.log`.

## Known limitations

- **No poison-message handling (v1).** A permanently-unsendable email (e.g. a
  malformed address) stays `EmailSent = 0` and is retried every run, logging an
  error each time. A future version may add a retry count or a failed-state
  sentinel.
- **Internal infrastructure details in config.** If this repository is public,
  keep real hostnames and addresses out of the committed `config/app.toml`
  (supply them via `EQH_*` env vars) or make the repository private.

## License

See `LICENSE`.
