import nox

nox.options.default_venv_backend = "uv"
PY = ["3.11", "3.12"]


def _install(session: nox.Session) -> None:
    session.run_install(
        "uv",
        "sync",
        "--frozen",
        "--group",
        "dev",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
        external=True,
    )


@nox.session(python=PY)
def fmt(session: nox.Session) -> None:
    _install(session)
    session.run("ruff", "check", "--fix", "src", "tests", "scripts")
    session.run("ruff", "format", "src", "tests", "scripts")


@nox.session(python=PY)
def lint(session: nox.Session) -> None:
    _install(session)
    session.run("ruff", "check", "--no-fix", "src", "tests", "scripts")
    session.run("ruff", "format", "--check", "src", "tests", "scripts")
    session.run("pyright")


@nox.session(python=PY)
def tests(session: nox.Session) -> None:
    _install(session)
    session.run("pytest", "--cov", "--cov-report=term-missing")
