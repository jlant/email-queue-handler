from __future__ import annotations

from pathlib import Path

from .settings import Settings, load_settings


def resolve_settings(config_path: Path | None = None) -> Settings:
    """Resolve runtime settings from the default or provided config path."""
    path = config_path or Path("config/app.toml")
    return load_settings(path)
