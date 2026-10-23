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
        # TODO(human): Replace this block with actual Zetaris client code
        # from zetaris import Client  # or whatever the actual import is
        raise ImportError(
            "Zetaris Python client not yet configured. "
            "Place sponsor docs in /docs/sponsor/ and update this script. "
            f"Expected connection: host={settings.zetaris_host}, "
            f"port={settings.zetaris_port}, "
            f"database={settings.zetaris_database}"
        )
    except ImportError as e:
        print(f"[smoke_zetaris] MISSING DEPENDENCY: {e}")
        print("[smoke_zetaris] What I need from you:")
        print("  1. Zetaris Python driver package name (pip install ???)")
        print("  2. Connection example code")
        print("  3. How to register CSV files as virtual tables")
        print("  4. Place docs in /docs/sponsor/zetaris_*.md")
        sys.exit(1)
    except Exception as e:
        print(f"[smoke_zetaris] CONNECTION FAILED: {e}")
        print(f"[smoke_zetaris] Check: ZETARIS_HOST={settings.zetaris_host}, "
              f"ZETARIS_PORT={settings.zetaris_port}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
