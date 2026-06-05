# Contributing to python-service-template

Thank you for considering contributing to Python Service Template.

To maintain code quality and a smooth workflow, please take a moment to review these guidelines.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) must be installed before anything else. It manages the
  Python environment, dependencies, and runs all tooling. See the uv documentation for
  installation instructions.

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

## Working on a project spawned from this template

If you are contributing to a project that was renamed from this template rather than to the
template itself, the CLI command and package name will differ from the examples above. Refer
to the [rename workflow](README.md#example---renaming-the-template) in the README for details.
