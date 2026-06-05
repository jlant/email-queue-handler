#!/usr/bin/env python3
"""Rename the python-service-template to a new project name.

Usage:
    python scripts/rename_template.py <new_pkg_name> <new_cli_name> <new_project_name>

Example:
    python scripts/rename_template.py my_service mst "My Service Template"

This produces:
    package/import name : my_service
    CLI command         : mst
    distribution name   : my-service  (auto-derived from package name)
    project display name: My Service Template
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# Template identity
OLD_PKG = "python_service_template"
OLD_CLI = "pst"
OLD_DIST = "python-service-template"
OLD_PROJ = "Python Service Template"

# File traversal config
SKIP_DIRS = {
    ".venv",
    ".git",
    ".nox",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
    ".pyright",
}

SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".pyc",
}

SKIP_FILES = {"uv.lock"}


# Validation functions
def validate_package_name(name: str) -> None:
    """Ensure the package name is a valid Python identifier."""
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        print(
            f"Error: '{name}' is not a valid Python package name.\n"
            "Use lowercase letters, digits, and underscores only (e.g. my_service).",
            file=sys.stderr,
        )
        sys.exit(1)


def validate_cli_name(name: str) -> None:
    """Ensure the CLI name is a simple lowercase identifier."""
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        print(
            f"Error: '{name}' is not a valid CLI name.\n"
            "Use lowercase letters, digits, and underscores only (e.g. mst).",
            file=sys.stderr,
        )
        sys.exit(1)


# File content replacement function
def replace_file_content(
    text: str,
    old_pkg: str,
    old_cli: str,
    old_dist: str,
    old_proj: str,
    new_pkg: str,
    new_cli: str,
    new_dist: str,
    new_proj: str,
) -> str:
    """Apply all template substitutions to a string.

    Note: Order matters - more specific patterns before general ones
    """
    # Project / distribution metadata
    text = text.replace(f'name = "{old_dist}"', f'name = "{new_dist}"')
    text = text.replace(f'DIST_NAME = "{old_dist}"', f'DIST_NAME = "{new_dist}"')
    text = text.replace(f'DEFAULT_APP_NAME = "{old_dist}"', f'DEFAULT_APP_NAME = "{new_dist}"')

    # Console script entry point
    text = text.replace(
        f'{old_cli} = "{old_pkg}.cli:app"',
        f'{new_cli} = "{new_pkg}.cli:app"',
    )

    # Package / import paths
    text = text.replace(f"from {old_pkg}.", f"from {new_pkg}.")
    text = text.replace(f'"{old_pkg}.', f'"{new_pkg}.')
    text = text.replace(f"src/{old_pkg}", f"src/{new_pkg}")

    # Human-facing CLI label in code / help output
    text = text.replace(f'CLI_NAME = "{old_cli}"', f'CLI_NAME = "{new_cli}"')

    # README / project title
    text = text.replace(f"# {old_proj}", f"# {new_proj}")

    # CLI help header
    text = text.replace(
        f"{old_proj} ({old_cli}) CLI Tool",
        f"{new_proj} ({new_cli.upper()}) CLI Tool",
    )

    # README CLI command references in code blocks
    text = text.replace(f"uv run {old_cli} ", f"uv run {new_cli} ")
    text = text.replace(f"uv run {old_cli}\n", f"uv run {new_cli}\n")

    # Environment variable prefix in README examples
    text = text.replace(f"{old_cli.upper()}_", f"{new_cli.upper()}_")

    return text


# Package directory rename function
def rename_package_directory(root: Path, old_pkg: str, new_pkg: str, dry_run: bool) -> None:
    """Rename the package directory."""
    src_dir = root / "src" / old_pkg
    dst_dir = root / "src" / new_pkg

    if not src_dir.exists():
        print(f"Warning: package directory '{src_dir}' not found - skipping rename.")
        return

    if dst_dir.exists():
        print(f"Error: destination '{dst_dir}' already exists.", file=sys.stderr)
        sys.exit(1)

    print(f"Renaming directory: {src_dir} -> {dst_dir}")
    if not dry_run:
        shutil.move(str(src_dir), str(dst_dir))


# File traversal function
def iter_files(root: Path):
    """Yield all files that should have content substitution (replacement) applied and
    skip directories and files that should not have substitution (replacement applied."""
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name in SKIP_FILES:
            continue
        yield path


# Apply substitutions to files function
def process_files(
    root: Path,
    old_pkg: str,
    old_cli: str,
    old_dist: str,
    old_proj: str,
    new_pkg: str,
    new_cli: str,
    new_dist: str,
    new_proj: str,
    dry_run: bool,
) -> int:
    """Apply substitutions to all elgible files. Returns the count of modified files."""
    modified_cnt = 0

    for path in iter_files(root):
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        updated = replace_file_content(
            original, old_pkg, old_cli, old_dist, old_proj, new_pkg, new_cli, new_dist, new_proj
        )

        if updated != original:
            print(f"  Updating: {path}")
            modified_cnt += 1
            if not dry_run:
                path.write_text(updated, encoding="utf-8")

    return modified_cnt


# Script entry point
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "new_pkg", metavar="new_pkg_name", help="New package/import name (e.g. my_service)"
    )
    parser.add_argument("new_cli", metavar="new_cli_name", help="New CLI command name (e.g. mst)")
    parser.add_argument(
        "new_proj", metavar="new_project_name", help='New project display name (e.g. "My Service")'
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing any files.",
    )

    return parser.parse_args()


# Main function
def main() -> None:
    args = parse_args()

    new_pkg: str = args.new_pkg
    new_cli: str = args.new_cli
    new_proj: str = args.new_proj
    dry_run: bool = args.dry_run

    validate_package_name(new_pkg)
    validate_cli_name(new_cli)

    # Derive distribution name from package name (underscores -> hyphens)
    new_dist = new_pkg.replace("_", "-")

    # Assign root directory from this file
    root = Path(__file__).parent.parent.resolve()

    if dry_run:
        print("Dry run - no files will be modified.\n")

    print("Renaming template:")
    print(f"  package name : {OLD_PKG!r} -> {new_pkg!r}")
    print(f"  CLI name     : {OLD_CLI!r} -> {new_cli!r}")
    print(f"  dist name    : {OLD_DIST!r} -> {new_dist!r}")
    print(f"  project name : {OLD_PROJ!r} -> {new_proj!r}")

    # Rename package directory
    rename_package_directory(root, OLD_PKG, new_pkg, dry_run)

    # Process all elgible files and return the count of modified files
    modified_cnt = process_files(
        root,
        OLD_PKG,
        OLD_CLI,
        OLD_DIST,
        OLD_PROJ,
        new_pkg,
        new_cli,
        new_dist,
        new_proj,
        dry_run,
    )

    print()
    action = "Would modify" if dry_run else "Modified"
    print(f"{action} {modified_cnt} file(s).")

    if not dry_run:
        print()
        print("Next steps:")
        print("  uv lock")
        print("  uv sync --all-extras --dev")
        print("  pre-commit install")
        print("  uv run nox -s fmt")
        print("  uv run nox -s lint")
        print("  uv run nox -s tests")


if __name__ == "__main__":
    main()
