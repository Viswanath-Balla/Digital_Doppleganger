"""Zetaris DataLayer implementation with automatic graceful degradation to DuckDBDataLayer."""

from __future__ import annotations

import asyncio
import csv
import logging
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from src.dd.adapters.base import DataLayer
from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer
from src.dd.config import get_settings

logger = logging.getLogger("dd.zetaris")


class ZetarisDataLayer(DataLayer):
    """Live DataLayer backed by the Zetaris Virtual Data Warehouse / PostgreSQL service."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        data_dir: Path | str | None = None,
    ) -> None:
        settings = get_settings()
        self.host = host or settings.zetaris_host
        self.port = port or settings.zetaris_port
        self.user = user or settings.zetaris_user
        self.password = password or settings.zetaris_password
        self.database = database or settings.zetaris_database
        self.data_dir = Path(data_dir) if data_dir else settings.data_dir

        # Test initial connection & seed tables if necessary
        self._ensure_tables_exist()

    def _get_connection(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            connect_timeout=5,
        )

    def _ensure_tables_exist(self) -> None:
        """Verify tables exist in Zetaris metastore; if missing, create and seed them from CSVs."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Check existing tables
                cur.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
                )
                existing = {row[0] for row in cur.fetchall()}

                expected_tables = [
                    "profile_fields",
                    "strava_activities",
                    "food_orders",
                    "calendar_events",
                    "social_posts",
                    "pharmacy_orders",
                ]

                for table in expected_tables:
                    if table not in existing and self.data_dir.exists():
                        csv_path = self.data_dir / f"{table}.csv"
                        if csv_path.exists():
                            self._create_and_seed_table(cur, table, csv_path)
            conn.commit()
        finally:
            conn.close()

    def _create_and_seed_table(
        self, cur: psycopg2.extensions.cursor, table_name: str, csv_path: Path
    ) -> None:
        """Create a table in Zetaris and populate from CSV data."""
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return

            cols_def = ", ".join(f'"{col}" TEXT' for col in header)
            cur.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols_def});')

            # Insert rows
            placeholders = ", ".join(["%s"] * len(header))
            insert_sql = f'INSERT INTO "{table_name}" ({", ".join(f"{col}" for col in header)}) VALUES ({placeholders});'
            rows = [tuple(row) for row in reader]
            if rows:
                cur.executemany(insert_sql, rows)

    def _sync_query(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if params:
                    cur.execute(sql, params)
                else:
                    cur.execute(sql)
                if cur.description is None:
                    conn.commit()
                    return []
                results = [dict(row) for row in cur.fetchall()]
                conn.commit()
                return results
        finally:
            conn.close()

    async def query(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Guarded asynchronous execution of SQL queries against Zetaris."""
        return await asyncio.to_thread(self._sync_query, sql, params)

    async def health_check(self) -> bool:
        """Verify Zetaris connectivity with a SELECT 1 query."""
        try:
            rows = await self.query("SELECT 1 AS ok;")
            return len(rows) == 1 and rows[0].get("ok") == 1
        except Exception:
            return False


async def create_data_layer(sample_mode: bool | None = None) -> tuple[DataLayer, bool]:
    """Factory creating DataLayer with automatic graceful fallback to DuckDB.

    Returns:
        (data_layer_instance, is_degraded)
    """
    settings = get_settings()
    is_sample = sample_mode if sample_mode is not None else settings.sample_mode

    if is_sample:
        return DuckDBDataLayer(sample_data_dir=settings.data_dir), False

    # Attempt live Zetaris connection
    try:
        zetaris_dl = ZetarisDataLayer(
            host=settings.zetaris_host,
            port=settings.zetaris_port,
            user=settings.zetaris_user,
            password=settings.zetaris_password,
            database=settings.zetaris_database,
            data_dir=settings.data_dir,
        )
        if await zetaris_dl.health_check():
            return zetaris_dl, False
        else:
            raise ConnectionError("Zetaris health check failed")
    except Exception as e:
        logger.warning(
            f"[dd] Zetaris live service unreachable ({type(e).__name__}: {e}). "
            "Falling back to DuckDBDataLayer (Degraded Mode)."
        )
        return DuckDBDataLayer(sample_data_dir=settings.data_dir), True
