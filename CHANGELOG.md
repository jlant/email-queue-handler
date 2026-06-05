# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-29

### Added

- Updated and improved `settings.py` and corresponding `test_settings.py`.
- Updated and improved `service.py`.


## [0.1.0] - 2026-04-24

### Added

- Added old project name as a variable in the `rename_template.py` script.

### Changed

- Using `DEFAULT_APP_NAME` from `settings.py` in `tests/test_config.py` instead of hard-coded app name
- Updated the string variable names in the `OLD` variable to be more clear and generic, and to not get
  replaced by the `rename_template.py` script.
- Updated the description in the `README.md` and the header text in `cli.py`

## [0.1.0] - 2026-04-23

### Removed

- Functionality that automatically removed the "## Example - renaming the template"
  section in the `README.md` file.


### Added

- Tests for the `rename_template.py` script in `tests/test_rename_template.py`.
- Additional tooling configuration in `pyproject.toml` and `noxfile.py` for `pytest` and `pyright`
  for the inclusion of the tests for the `rename_template.py` script.

## [0.1.0] - 2026-04-22

### Added

- Initial project structure using `src/` layout with `hatchling` as the build backend.
- CLI interface using `Typer` with `hello`, `read-config`, and `run` commands.
- `Settings` dataclass with layered configuration: defaults → TOML file → environment variables.
- `Service` class with `start()`, `run()`, and `stop()` lifecycle methods.
- Optional `pipeline.py` module for YAML-driven multi-step orchestration (requires `yaml` extra).
- `configure_logging()` for structured application logging at startup.
- `pyproject.toml` with `uv` as the package manager and `hatchling` as the build backend.
- `nox` sessions for `fmt`, `lint`, and `tests` using `uv sync --frozen` for reproducible installs.
- `ruff` for linting and formatting with rules: `E`, `F`, `I`, `UP`, `B`, `SIM`, `C4`, `PTH`, `RUF`.
- `pyright` in strict mode for static type checking.
- `pytest` with `pytest-cov` enforcing 80% minimum coverage.
- `pre-commit` hooks for `ruff`, `ruff-format`, and common file hygiene checks.
- GitHub Actions CI workflow running lint and tests on Python 3.11 and 3.12.
- MIT License.

### Changed

- Replaced `rename_template.sh` shell script with `rename_template.py` Python script for
  cross-platform reliability, input validation, and a `--dry-run` mode.
- Replaced the environment variable `<CLI_NAME>_` prefix in `settings.py` with an `ENV_PREFIX = "APP"` for
  a generic, self-documenting, and import-free way to prefix the environment variables, and it also works
  correctly after any rename without modification.

### Fixed

- Text replacement in `replace_template.py` for console script entry point by reordering
  the replacements so the console script entry point is handled before the general
  `"{old_pkg}.` replacement

[Unreleased]: https://github.com/jlant/python-service-template/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jlant/python-service-template/releases/tag/v0.1.0
