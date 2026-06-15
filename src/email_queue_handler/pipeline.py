from __future__ import annotations

# Optional orchestration module:
# - Only used if you opt in to YAML (`uv sync --extra yaml --dev`)
# - Kept separate so TOML stays the default for app config
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from typing import Any


@dataclass
class Step:
    name: str
    cmd: list[str]


def load_pipeline(path: Path) -> list[Step]:
    import yaml

    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    steps = data.get("steps", [])
    return [Step(name=s["name"], cmd=list(s["cmd"])) for s in steps]


def run_pipeline(path: Path) -> int:
    steps = load_pipeline(path)
    for step in steps:
        completed = run(step.cmd, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0
