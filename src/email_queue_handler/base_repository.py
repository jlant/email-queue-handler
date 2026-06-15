from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

import pyodbc


class BaseRepository:
    def __init__(self, connection_factory: Callable[[], AbstractContextManager[Any]]):
        """Expects a lambda or function that yields a context-managed connection."""
        self._connection_factory = connection_factory

    def _row_to_dict(self, cursor: pyodbc.Cursor, row: pyodbc.Row) -> dict[str, Any]:
        """Helper to cleanly extract key-value data using SQL output names."""
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row, strict=True))
