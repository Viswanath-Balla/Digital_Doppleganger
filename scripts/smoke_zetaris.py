"""Smoke test: Zetaris connectivity.

Run: python scripts/smoke_zetaris.py

In SAMPLE_MODE, skips with exit 0.
Otherwise, attempts to connect to Zetaris and run basic queries.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dd.config import get_settings


async def main() -> None:
    settings = get_settings()

    if settings.sample_mode:
        print("[smoke_zetaris] SAMPLE_MODE=true -- skipping Zetaris smoke test.")
        print("[smoke_zetaris] To test Zetaris, set SAMPLE_MODE=false in .env")
        return

    # --- Live Zetaris test ---
    print(f"[smoke_zetaris] Connecting to Zetaris at {settings.zetaris_host}:{settings.zetaris_port}")

    # TODO(human): Replace with real Zetaris connection code.
    # Need docs in /docs/sponsor/ for:
    #   - Zetaris Python driver / JDBC bridge
    #   - Connection string format
    #   - Authentication method
    #   - How to register CSV/Parquet sources as tables
    #
    # For now, we attempt an import and give a clear error if missing.

    try:
        import psycopg2

        conn = psycopg2.connect(
            host=settings.zetaris_host,
            port=settings.zetaris_port,
            user=settings.zetaris_user,
            password=settings.zetaris_password,
            database=settings.zetaris_database,
            connect_timeout=5,
        )
        cur = conn.cursor()
        cur.execute("SELECT 1 AS ok;")
        result = cur.fetchone()
        print(f"[smoke_zetaris] SUCCESS! SELECT 1 returned: {result}")

        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        )
        tables = [t[0] for t in cur.fetchall()]
        print(f"[smoke_zetaris] Existing tables in '{settings.zetaris_database}': {tables}")
        conn.close()

    except Exception as e:
        print(f"[smoke_zetaris] CONNECTION FAILED: {type(e).__name__}: {e}")
        print(f"[smoke_zetaris] Check: ZETARIS_HOST={settings.zetaris_host}, "
              f"ZETARIS_PORT={settings.zetaris_port}, "
              f"ZETARIS_DATABASE={settings.zetaris_database}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
