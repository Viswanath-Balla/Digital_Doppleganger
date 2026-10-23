"""Nightshift LLM client implementation targeting Nemotron models with retries and graceful fallback."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel

from src.dd.adapters.base import LLMClient, LLMResponse
from src.dd.adapters.replay_llm_client import ReplayLLMClient
from src.dd.config import get_settings

logger = logging.getLogger("dd.nightshift")


class NightshiftLLMClient(LLMClient):
    """Production LLM client connecting to Meterless Nightshift serving Nemotron models."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_sec: float = 60.0,
        max_retries: int = 2,
        default_max_tokens: int = 500,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.nightshift_base_url).rstrip("/")
        self.api_key = api_key or settings.nightshift_api_key
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.default_max_tokens = default_max_tokens

        # Agent-to-Model mapping
        self.model_extractor = settings.model_extractor
        self.model_redteam = settings.model_redteam
        self.model_verifier = settings.model_verifier

    def _get_model_for_agent(self, agent: str) -> str:
        """Map agent role to appropriate model identifier."""
        if agent in ("red_team", "redteam"):
            return self.model_redteam
        elif agent in ("verifier",):
            return self.model_verifier
        else:
            return self.model_extractor

    async def complete(
        self,
        agent: str,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Execute chat completion against Nightshift with timeouts and retries."""
        model = self._get_model_for_agent(agent)
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens or self.default_max_tokens,
        }

        # If structured output schema is provided, format prompt or json_mode
        if response_schema:
            payload["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    resp = await client.post(url, headers=headers, json=payload)

                    if resp.status_code in (429, 502, 503, 504):
                        # Rate limit or transient gateway error -> retry
                        if attempt < self.max_retries:
                            wait_time = 1.0 * (2 ** attempt)
                            logger.warning(
                                f"[Nightshift] Status {resp.status_code}. Retrying in {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            continue

                    resp.raise_for_status()
                    data = resp.json()

                    latency = (time.perf_counter() - t0) * 1000
                    content = data["choices"][0]["message"]["content"]
                    returned_model = data.get("model", model)

                    # Validate response schema if specified
                    if response_schema:
                        try:
                            parsed_json = json.loads(content)
                            response_schema.model_validate(parsed_json)
                        except Exception as val_err:
                            logger.warning(
                                f"[Nightshift] Schema validation warning: {val_err}"
                            )

                    return LLMResponse(
                        content=content,
                        model=returned_model,
                        latency_ms=latency,
                        retries=attempt,
                        raw=data,
                    )

            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = 1.0 * (2 ** attempt)
                    logger.warning(
                        f"[Nightshift] {type(e).__name__} on attempt {attempt + 1}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[Nightshift] All {self.max_retries + 1} attempts failed: {e}")
                    raise

        raise RuntimeError(f"Nightshift complete failed: {last_error}")


async def create_llm_client(sample_mode: bool | None = None) -> tuple[LLMClient, bool]:
    """Factory creating LLMClient with automatic graceful fallback to ReplayLLMClient.

    Returns:
        (llm_client_instance, is_degraded)
    """
    settings = get_settings()
    is_sample = sample_mode if sample_mode is not None else settings.sample_mode

    if is_sample:
        return ReplayLLMClient(), False

    # Check for placeholder API key
    if (
        not settings.nightshift_api_key
        or settings.nightshift_api_key.startswith("PLACEHOLDER")
    ):
        logger.warning(
            "[dd] NIGHTSHIFT_API_KEY is unconfigured or a placeholder. "
            "Falling back to ReplayLLMClient (Degraded Mode)."
        )
        return ReplayLLMClient(), True

    client = NightshiftLLMClient(
        base_url=settings.nightshift_base_url,
        api_key=settings.nightshift_api_key,
        timeout_sec=30.0,
        max_retries=2,
    )

    # Health check ping
    try:
        # Quick 5-token ping to verify connectivity
        async with httpx.AsyncClient(timeout=5.0) as http_check:
            res = await http_check.post(
                f"{client.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {client.api_key}"},
                json={
                    "model": client.model_extractor,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            if res.status_code == 200:
                return client, False
            else:
                raise ConnectionError(f"HTTP {res.status_code}: {res.text[:100]}")
    except Exception as e:
        logger.warning(
            f"[dd] Nightshift endpoint unreachable ({type(e).__name__}: {e}). "
            "Falling back to ReplayLLMClient (Degraded Mode)."
        )
        return ReplayLLMClient(), True
