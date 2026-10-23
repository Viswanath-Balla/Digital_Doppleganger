"""Record real model outputs from Nightshift / Nemotron into cache/llm_replay.jsonl.

Enables sample mode to reproduce genuine Nemotron reasoning offline.
Run: python scripts/record_llm_cache.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.dd.adapters.nightshift_llm_client import NightshiftLLMClient
from src.dd.adapters.replay_llm_client import _prompt_hash
from src.dd.config import get_settings


async def record_cache() -> None:
    settings = get_settings()
    print("=" * 70)
    print(" RECORDING NIGHTSHIFT / NEMOTRON RESPONSES FOR REPLAY CACHE")
    print(f" Nightshift Endpoint: {settings.nightshift_base_url}")
    print(f" Model Red-Team:     {settings.model_redteam}")
    print(f" Model Verifier:     {settings.model_verifier}")
    print("=" * 70)

    client = NightshiftLLMClient(
        base_url=settings.nightshift_base_url,
        api_key=settings.nightshift_api_key,
        timeout_sec=60.0,
        max_retries=2,
        default_max_tokens=250,
    )

    cache_file = settings.cache_dir / "llm_replay.jsonl"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    # Scenarios to record from live Nemotron
    prompts_to_record = [
        (
            "extractor",
            [
                {"role": "system", "content": "You are an extractor agent. Summarize key privacy facts."},
                {"role": "user", "content": "Extract location and routine facts from Strava and food deliveries."},
            ],
        ),
        (
            "red_team",
            [
                {"role": "system", "content": "You are a red-team privacy analyst."},
                {"role": "user", "content": "Propose adversarial privacy inferences for Profile A based on GPS cluster and food orders."},
            ],
        ),
        (
            "red_team",
            [
                {"role": "system", "content": "You are a red-team privacy analyst."},
                {"role": "user", "content": "Verifier rejected the night shift claim. Revise your hypothesis with lower confidence."},
            ],
        ),
        (
            "verifier",
            [
                {"role": "system", "content": "You are a verifier agent evaluating an inference."},
                {"role": "user", "content": "Evaluate claim: Subject works regular night shifts based on single late night order."},
            ],
        ),
        (
            "verifier",
            [
                {"role": "system", "content": "You are a verifier agent evaluating an inference."},
                {"role": "user", "content": "Evaluate claim: Subject resides at 742 Evergreen Terr, Springfield based on GPS cluster and food deliveries."},
            ],
        ),
    ]

    recorded_count = 0
    with open(cache_file, "a", encoding="utf-8") as f:
        for agent, msgs in prompts_to_record:
            key = _prompt_hash(agent, msgs)
            print(f"\n[record] Calling live {agent} on {client._get_model_for_agent(agent)}...")

            try:
                resp = await client.complete(agent=agent, messages=msgs)
                entry = {
                    "key": key,
                    "agent": agent,
                    "model": resp.model,
                    "content": resp.content,
                    "latency_ms": resp.latency_ms,
                    "retries": resp.retries,
                }
                f.write(json.dumps(entry) + "\n")
                recorded_count += 1
                print(f"  -> SUCCESS: model={resp.model}, latency={resp.latency_ms:.1f}ms")
            except Exception as e:
                print(f"  -> ERROR: {e}")

    print("\n" + "=" * 70)
    print(f" Successfully recorded {recorded_count} live responses into {cache_file}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(record_cache())
