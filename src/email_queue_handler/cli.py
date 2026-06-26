from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated

import typer
from rich import print

from .config import resolve_settings
from .logging import configure_logging
from .service import Service
from .settings import Settings

DIST_NAME = "email-queue-handler"
CLI_NAME = "eqh"

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",  # Allows for help text to use [bold], [green], etc.
    epilog="Made with :heart:  by [blue]Jeremiah Lant[/blue]",  # Footer text
)


def version_callback(value: bool):
    if value:
        try:
            v = version(DIST_NAME)
        except PackageNotFoundError:
            v = "0.0.0"
        print(f"{CLI_NAME} {v}")
        raise typer.Exit()


def _mask(value: str) -> str:
    """Return masked credential string for safe display."""
    return "***" if value else "(not set)"


@app.callback()
def main(
    ctx: typer.Context,
    version_opt: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show app version and exit.",
    ),
):
    """
    [green] Email Queue Handler (EQH) CLI Tool[/green] :rocket:

    A minimal, production-grade Python service with a CLI interface.
    """
    _ = ctx
    _ = version_opt


@app.command()
def read_config(
    config: Annotated[Path, typer.Option("--config", "-c", exists=False)] = Path("config/app.toml"),
) -> None:
    """Read config and print resolved settings. Credentials are masked."""
    settings: Settings = resolve_settings(config)

    print("[bold]App[/bold]")
    print(f"  app_name={settings.app_name!r}")
    print(f"  env={settings.env!r}")
    print(f"  log_level={settings.log_level!r}")
    print(f"  log_file={settings.log_file!r}")

    print("[bold]SQL Server[/bold]")
    print(f"  sqlserver_host={settings.sqlserver_host!r}")
    print(f"  sqlserver_database={settings.sqlserver_database!r}")
    print(f"  sqlserver_user={settings.sqlserver_user!r}")
    print(f"  sqlserver_password={_mask(settings.sqlserver_password)}")

    print("[bold]Email[/bold]")
    print(f"  email_smtp_server={settings.email_smtp_server!r}")
    print(f"  email_smtp_port={settings.email_smtp_port!r}")
    print(f"  email_send_from={settings.email_send_from!r}")
    print(f"  email_send_to={settings.email_send_to!r}")
    print(f"  email_password={_mask(settings.email_password)}")


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c", exists=False)] = Path("config/app.toml"),
) -> None:
    """Run the service once over the email queue.

    Exits 0 on a clean run (even if some individual emails failed and were
    left for retry). Exits 1 on a run-level failure (database or SMTP
    unreachable), so a scheduler can detect and react to a broken run.
    """
    settings = resolve_settings(config)
    configure_logging(settings)

    service = Service(settings)
    service.start()
    try:
        summary = service.run()
    finally:
        service.stop()

    if summary.run_failed:
        raise typer.Exit(code=1)
