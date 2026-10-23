"""DuckDB-backed DataLayer implementation for sample mode and local execution.

Mounts CSV files from data/sample/ as relational tables in DuckDB.
Provides standard SQL query execution, joins, aggregations, and window functions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import duckdb

from src.dd.adapters.base import DataLayer
from src.dd.config import get_settings


class DuckDBDataLayer(DataLayer):
    """DataLayer implementation backed by an in-process DuckDB engine."""

    def __init__(
        self,
        sample_data_dir: Path | str | None = None,
        db_path: str = ":memory:",
    ) -> None:
        self._db_path = db_path
        self._sample_data_dir = (
            Path(sample_data_dir) if sample_data_dir else get_settings().data_dir
        )
        self._con = duckdb.connect(database=self._db_path)
        self._registered_tables: list[str] = []
        self._init_tables()

    def _init_tables(self) -> None:
        """Register all CSV files in sample_data_dir as DuckDB tables."""
        if not self._sample_data_dir.exists():
            return

        # Ensure consistent UTC timestamps across all local client timezones
        self._con.execute("SET TimeZone = 'UTC';")

        for csv_file in self._sample_data_dir.glob("*.csv"):
            table_name = csv_file.stem
            # Register using forward slashes for cross-platform DuckDB compatibility
            escaped_path = str(csv_file.resolve()).replace("\\", "/")
            self._con.execute(
                f"CREATE OR REPLACE TABLE {table_name} AS "
                f"SELECT * FROM read_csv_auto('{escaped_path}', header=true);"
            )
            self._registered_tables.append(table_name)

    @property
    def registered_tables(self) -> list[str]:
        """Return list of table names registered in this DuckDB instance."""
        return list(self._registered_tables)

    def _sync_query(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Synchronous query runner executed in a threadpool."""
        cursor = self._con.execute(sql, params or {})
        if cursor.description is None:
            return []
        cols = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(cols, row)) for row in rows]

    async def query(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute SQL query asynchronously via threadpool and return rows as dicts."""
        return await asyncio.to_thread(self._sync_query, sql, params)

    async def health_check(self) -> bool:
        """Verify DuckDB instance responsiveness."""
        try:
            res = await self.query("SELECT 1 AS ok")
            return len(res) == 1 and res[0].get("ok") == 1
        except Exception:
            return False

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._con.close()
