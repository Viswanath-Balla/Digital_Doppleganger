"""In-memory DataLayer for sample mode and testing.

Stores tables as plain dicts.  Supports trivial SQL parsing (enough for
smoke tests and unit tests).  Phase 1 will add DuckDBDataLayer for real
SQL support; this one is purely for "does the interface work?" checks.
"""

from __future__ import annotations

import re
from typing import Any

from src.dd.adapters.base import DataLayer


class SampleDataLayer(DataLayer):
    """In-memory data layer backed by a Python dict of tables."""

    def __init__(self, tables: dict[str, list[dict[str, Any]]] | None = None):
        self._tables: dict[str, list[dict[str, Any]]] = tables or {}

    # -- public helpers (not part of the abstract interface) --

    def load_table(self, name: str, rows: list[dict[str, Any]]) -> None:
        """Register a table with the given rows."""
        self._tables[name] = rows

    # -- DataLayer interface --

    async def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Very basic SQL handling — just enough for smoke tests.

        Supports:
        - ``SELECT 1`` → ``[{"1": 1}]``
        - ``SELECT * FROM <table>`` → all rows
        - ``SELECT * FROM <table> WHERE <col> = '<value>'`` → filtered rows
        - ``SELECT * FROM <table> LIMIT <n>`` → first n rows
        """
        sql_stripped = sql.strip().rstrip(";")

        # SELECT 1
        if re.fullmatch(r"SELECT\s+1", sql_stripped, re.IGNORECASE):
            return [{"1": 1}]

        # SELECT * FROM <table> [WHERE ...] [LIMIT ...]
        m = re.match(
            r"SELECT\s+\*\s+FROM\s+(\w+)"
            r"(?:\s+WHERE\s+(\w+)\s*=\s*'([^']*)')?"
            r"(?:\s+LIMIT\s+(\d+))?",
            sql_stripped,
            re.IGNORECASE,
        )
        if m:
            table_name = m.group(1)
            rows = self._tables.get(table_name, [])

            # Optional WHERE clause
            if m.group(2) and m.group(3):
                col, val = m.group(2), m.group(3)
                rows = [r for r in rows if str(r.get(col)) == val]

            # Optional LIMIT clause
            if m.group(4):
                rows = rows[: int(m.group(4))]

            return rows

        raise ValueError(f"SampleDataLayer cannot parse SQL: {sql}")

    async def health_check(self) -> bool:
        """Always healthy — it is in-memory."""
        return True
