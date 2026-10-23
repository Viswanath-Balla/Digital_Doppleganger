"""CLI entrypoint for running the Digital Doppelgänger evaluation benchmark harness.

Usage:
    python -m src.dd.eval --sample
    python -m src.dd.eval --live
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.dd.config import get_settings
from src.dd.eval.evaluator import AuditEvaluator
from src.dd.eval.reporter import EvalReporter


async def run_benchmark(sample_mode: bool) -> None:
    settings = get_settings()
    evaluator = AuditEvaluator()

    suite_result = await evaluator.evaluate_all(sample_mode=sample_mode)

    # Print terminal scorecard
    table_str = EvalReporter.format_terminal_table(suite_result)
    print(table_str)

    # Export reports
    reports_dir = settings.project_root / "reports"
    json_path, md_path = EvalReporter.save_benchmark_artifacts(suite_result, reports_dir)
    print(f"\n[eval] Benchmark JSON exported to:     {json_path}")
    print(f"[eval] Benchmark Summary exported to:  {md_path}\n")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Digital Doppelgänger Evaluation Harness")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run benchmark against live Zetaris and Nightshift services",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run benchmark in offline sample mode (DuckDB + replay cache)",
    )
    args = parser.parse_args()

    settings = get_settings()
    # Default to sample mode unless explicitly asked for --live or SAMPLE_MODE=false in .env
    sample_mode = True
    if args.live:
        sample_mode = False
    elif args.sample:
        sample_mode = True
    else:
        sample_mode = settings.sample_mode

    asyncio.run(run_benchmark(sample_mode=sample_mode))


if __name__ == "__main__":
    main()
