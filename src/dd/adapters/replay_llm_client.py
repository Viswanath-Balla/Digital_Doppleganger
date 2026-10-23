"""Replay and deterministic stub LLM client.

Supports record/replay from cache/llm_replay.jsonl.
When running in SAMPLE_MODE without cached network calls, generates deterministic,
structured responses for each agent role without making external HTTP requests.
Clearly marked for Phase 4 where Nightshift / Nemotron will be wired.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.dd.adapters.base import LLMClient, LLMResponse
from src.dd.config import get_settings


def _prompt_hash(agent: str, messages: list[dict[str, str]]) -> str:
    """Generate a stable hash for agent name + message contents."""
    canonical = json.dumps({"agent": agent, "messages": messages}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


class ReplayLLMClient(LLMClient):
    """LLMClient implementation with record/replay cache and deterministic sample fallback."""

    def __init__(self, cache_file: Path | str | None = None) -> None:
        settings = get_settings()
        self._cache_file = (
            Path(cache_file) if cache_file else settings.cache_dir / "llm_replay.jsonl"
        )
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached completions from JSONL file if it exists."""
        if not self._cache_file.exists():
            return
        try:
            with open(self._cache_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = json.loads(line)
                        key = record.get("key")
                        if key:
                            self._cache[key] = record
        except Exception:
            # Corrupted or unreadable cache falls back to empty
            self._cache = {}

    def _record_cache(self, key: str, agent: str, response: LLMResponse) -> None:
        """Append a recorded response to the cache file."""
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "key": key,
            "agent": agent,
            "model": response.model,
            "content": response.content,
            "latency_ms": response.latency_ms,
            "retries": response.retries,
        }
        self._cache[key] = record
        try:
            with open(self._cache_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

    async def complete(
        self,
        agent: str,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Return completion from cache, live API (Phase 4), or deterministic sample generator."""
        t0 = time.perf_counter()
        key = _prompt_hash(agent, messages)

        # 1. Check Replay Cache
        if key in self._cache:
            cached = self._cache[key]
            latency = (time.perf_counter() - t0) * 1000
            return LLMResponse(
                content=cached["content"],
                model=f"{cached['model']} (replayed)",
                latency_ms=latency,
                retries=0,
            )

        settings = get_settings()

        # 2. Live API Branch — TODO(phase4): Implement live NightshiftLLMClient calls here
        if not settings.sample_mode:
            # Placeholder for live Nightshift completion
            raise NotImplementedError(
                "Live Nightshift calls are configured in Phase 4. Set SAMPLE_MODE=true."
            )

        # 3. Deterministic Sample Generation (Sample Mode)
        content = self._generate_sample_response(agent, messages, response_schema)
        latency = (time.perf_counter() - t0) * 1000

        # Model tagging per agent for traceability
        if agent in ("red_team", "verifier"):
            model_name = settings.model_redteam if settings.model_redteam != "sample-stub" else "nemotron-sample-stub"
        else:
            model_name = settings.model_extractor if settings.model_extractor != "sample-stub" else "extractor-sample-stub"

        response = LLMResponse(
            content=content,
            model=model_name,
            latency_ms=latency,
            retries=0,
        )

        # Record into memory cache
        self._cache[key] = {
            "key": key,
            "agent": agent,
            "model": model_name,
            "content": content,
            "latency_ms": latency,
            "retries": 0,
        }
        return response

    def _generate_sample_response(
        self,
        agent: str,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel] | None,
    ) -> str:
        """Deterministic generator for agent roles in sample mode."""
        prompt_text = "\n".join(m.get("content", "") for m in messages)

        if agent == "extractor":
            return json.dumps({
                "summary": "Extracted key entities and patterns from data fragments",
                "extracted_fields": ["location", "routine", "absence"],
            })

        if agent == "red_team":
            # If prompt mentions revising or rejected nightshift claim
            if "night shift" in prompt_text.lower() and "reject" in prompt_text.lower():
                return json.dumps({
                    "action": "revise",
                    "reasoning": "Acknowledged lack of weekday overnight telemetry. Downgrading claim to weekend late-night food delivery.",
                    "claim": "Orders occasional late-night takeout on weekend evenings",
                    "category": "lifestyle",
                    "confidence": 0.65,
                })
            return json.dumps({
                "action": "propose",
                "reasoning": "Synthesized cross-source correlations across Strava, orders, and calendar.",
            })

        if agent == "verifier":
            if "night shift" in prompt_text.lower():
                return json.dumps({
                    "label": "speculation",
                    "confidence": 0.20,
                    "rationale": "Single Saturday late-night takeout order at 23:45 does not establish ongoing night shift employment. Calendar shows standard 09:30 AM engineering standups.",
                    "falsification_condition": "Employment records or consecutive weekday overnight activity timestamps.",
                    "strengthening_condition": "Regular 00:00-08:00 recurring calendar shifts or commute patterns.",
                })
            return json.dumps({
                "label": "supported",
                "confidence": 0.90,
                "rationale": "Multi-source correlation between GPS coordinate cluster and food delivery address.",
                "falsification_condition": "Evidence of relocation or shared account usage.",
                "strengthening_condition": "Additional independent delivery or utility records.",
            })

        # Generic fallback
        return json.dumps({
            "agent": agent,
            "status": "completed",
            "message": "Deterministic sample mode response",
        })
