"""Stub LLM client for sample / offline mode.

Returns canned responses with ``model="sample-stub"``.  No network calls.
Phase 3 will add a record/replay client; Phase 4 adds NightshiftLLMClient.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from src.dd.adapters.base import LLMClient, LLMResponse


class SampleLLMClient(LLMClient):
    """Deterministic stub that echoes prompts — no network, no API key needed."""

    MODEL_NAME = "sample-stub"

    async def complete(
        self,
        agent: str,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Return a canned response that includes the agent name and last user message."""
        t0 = time.perf_counter()

        # Extract the last user message for echo
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break

        content = (
            f'{{"agent": "{agent}", '
            f'"echo": "{last_user_msg[:200]}", '
            f'"stub": true}}'
        )

        latency = (time.perf_counter() - t0) * 1000

        return LLMResponse(
            content=content,
            model=self.MODEL_NAME,
            latency_ms=latency,
            retries=0,
        )
