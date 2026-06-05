import sys
from pathlib import Path

import pytest

from python_service_template.pipeline import Step, load_pipeline, run_pipeline

PIPELINE_YAML = """
steps:
  - name: echo hello
    cmd: [echo, hello]
  - name: echo world
    cmd: [echo, world]
""".strip()


@pytest.fixture()
def pipeline_file(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline.yml"
    path.write_text(PIPELINE_YAML, encoding="utf-8")
    return path


def test_load_pipeline_returns_steps(pipeline_file: Path) -> None:
    steps = load_pipeline(pipeline_file)
    assert len(steps) == 2
    assert steps[0] == Step(name="echo hello", cmd=["echo", "hello"])
    assert steps[1] == Step(name="echo world", cmd=["echo", "world"])


def test_load_pipeline_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    steps = load_pipeline(path)
    assert steps == []


def test_run_pipeline_success(pipeline_file: Path) -> None:
    result = run_pipeline(pipeline_file)
    assert result == 0


def test_run_pipeline_failure(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.yml"
    # Use a command guaranteed to fail on any platform
    path.write_text(
        f"""
steps:
  - name: fail
    cmd: [{sys.executable}, -c, "import sys; sys.exit(1)"]
""".strip(),
        encoding="utf-8",
    )
    result = run_pipeline(path)
    assert result != 0
