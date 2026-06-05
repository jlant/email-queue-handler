# Python Service Template

A minimal, production-grade Python service with a CLI interface.

## Tools

- [uv](https://docs.astral.sh/uv/) — package and environment management
- [ruff](https://docs.astral.sh/ruff/) — linting and formatting
- [pyright](https://github.com/microsoft/pyright) — static type checking
- [pytest](https://pytest.org) — testing with coverage enforcement
- [nox](https://nox.thea.codes) — session automation
- [pre-commit](https://pre-commit.com) — git hook management
- [Typer](https://typer.tiangolo.com) — CLI interface
- TOML as the default config format
- YAML only for multi-step orchestration
- `src/` layout

## Quick start

```bash
uv run pst --help
uv run pst hello
uv run pst hello -n Jeremiah
uv run pst read-config
uv run pst run
APP_LOG_LEVEL=DEBUG APP_RUN_SECONDS=0 uv run pst run
```

## Development workflow

```bash
uv lock
uv sync --all-extras --dev
pre-commit install

# Format
uv run nox -s fmt

# Lint + type check
uv run nox -s lint

# Run tests
uv run nox -s tests

# Check template reads config file
uv run pst read-config

# Check template runs service
uv run pst run
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details on the development workflow and
guidelines for contributors.

## Example - renaming the template

After creating a new repo with this template, rename it by running the `rename_template.py`
script:

```bash
# Preview first
python scripts/rename_template.py my_service mst "My Service" --dry-run

# Then apply
python scripts/rename_template.py my_service mst "My Service"
```

Then finalize and verify everything is working:

```bash
uv lock
uv sync --all-extras --dev
pre-commit install

# Format
uv run nox -s fmt

# Lint + type check
uv run nox -s lint

# Run tests
uv run nox -s tests

# Check template reads config file
uv run <new_cli_name> read-config

# Check template runs service
uv run <new_cli_name> run
```
