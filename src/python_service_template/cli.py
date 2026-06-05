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

DIST_NAME = "python-service-template"
CLI_NAME = "pst"

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
    [green] Python Service Template (pst) CLI Tool[/green] :rocket:

    A minimal, production-grade Python service with a CLI interface.
    """
    _ = ctx
    _ = version_opt


@app.command()
def hello(
    name: str = typer.Option("world", "--name", "-n"),
) -> None:
    """Example command that prints a greeting."""
    print(f"[bold green]Hello, {name}![/bold green]")


@app.command()
def read_config(
    config: Annotated[Path, typer.Option("--config", "-c", exists=False)] = Path("config/app.toml"),
) -> None:
    """Read config and print resolved settings"""
    settings: Settings = resolve_settings(config)
    print(f"app_name={settings.app_name!r}")
    print(f"log_level={settings.log_level!r}")
    print(f"env={settings.env!r}")
    print(f"run_seconds={settings.run_seconds!r}")


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c", exists=False)] = Path("config/app.toml"),
) -> None:
    """Run the service lifecycle once."""
    settings = resolve_settings(config)
    configure_logging(settings)

    service = Service(settings)
    service.start()
    try:
        service.run()
    finally:
        service.stop()
