"""Digital Doppelgänger — main entrypoint.

Usage: python -m src.dd.main --profile A
"""

from __future__ import annotations

import argparse
import sys

from src.dd.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Digital Doppelgänger privacy audit")
    parser.add_argument(
        "--profile",
        type=str,
        default="A",
        choices=["A", "B", "C"],
        help="Profile to audit (A, B, or C)",
    )
    args = parser.parse_args()

    settings = get_settings()
    mode = "SAMPLE" if settings.sample_mode else "LIVE"
    print(f"[dd] Mode: {mode}")
    print(f"[dd] Profile: {args.profile}")

    # TODO(phase3): Import and run the agent orchestration loop
    print("[dd] Agent loop not yet implemented -- see Phase 3.")
    print("[dd] Scaffold is ready. Run `make test` to verify.")


if __name__ == "__main__":
    main()
