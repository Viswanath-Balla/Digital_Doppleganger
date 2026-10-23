"""Smoke test: Nightshift / Nemotron connectivity.

Run: python scripts/smoke_nightshift.py

In SAMPLE_MODE, skips with exit 0.
Otherwise, sends a tiny completion request and prints the model name.
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
        print("[smoke_nightshift] SAMPLE_MODE=true -- skipping Nightshift smoke test.")
        print("[smoke_nightshift] To test Nightshift, set SAMPLE_MODE=false in .env")
        return

    # --- Live Nightshift test ---
    print(f"[smoke_nightshift] Connecting to Nightshift at {settings.nightshift_base_url}")

    if not settings.nightshift_api_key or settings.nightshift_api_key.startswith("PLACEHOLDER"):
        print("[smoke_nightshift] MISSING: NIGHTSHIFT_API_KEY is not set or is a placeholder.")
        print("[smoke_nightshift] Set it in .env and retry.")
        sys.exit(1)

    try:
        import httpx

        # Nightshift is assumed to be OpenAI-compatible (TODO(human): confirm from docs)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.nightshift_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.nightshift_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.model_redteam,  # Use the Nemotron model
                    "messages": [
                        {"role": "user", "content": "Say 'hello' in one word."}
                    ],
                    "max_tokens": 10,
                },
            )
            response.raise_for_status()
            data = response.json()

            model_name = data.get("model", "UNKNOWN")
            content = data["choices"][0]["message"]["content"]

            print(f"[smoke_nightshift] SUCCESS")
            print(f"[smoke_nightshift] Model: {model_name}")
            print(f"[smoke_nightshift] Response: {content}")

    except httpx.ConnectError as e:
        print(f"[smoke_nightshift] CONNECTION FAILED: {e}")
        print(f"[smoke_nightshift] Check: NIGHTSHIFT_BASE_URL={settings.nightshift_base_url}")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"[smoke_nightshift] HTTP ERROR {e.response.status_code}: {e.response.text[:500]}")
        sys.exit(1)
    except Exception as e:
        print(f"[smoke_nightshift] UNEXPECTED ERROR: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
