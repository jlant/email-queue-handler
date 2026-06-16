from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager

import pyodbc


class BaseRepository:
    """Shared plumbing for repositories that talk to SQL Server via pyodbc.

    The repository depends on a *connection factory* rather than a live
    connection. The factory is a zero-argument callable that returns a
    context-managed connection (see ``sqlserver_db.get_connection``). This
    keeps two concerns separate:

    - *how* a connection is opened and closed (the factory's job), and
    - *what* queries are run against it (the repository's job).

    Because the dependency is a plain callable, tests can pass a factory that
    yields a fake connection - no real database required.
    """

    def __init__(
        self,
        connection_factory: Callable[[], AbstractContextManager[pyodbc.Connection]],
    ) -> None:
        self._connection_factory = connection_factory
