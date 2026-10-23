"""Tests for Phase 4: Live adapters (Zetaris, Nightshift/Nemotron) and graceful degradation fallbacks."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer
from src.dd.adapters.nightshift_llm_client import NightshiftLLMClient, create_llm_client
from src.dd.adapters.replay_llm_client import ReplayLLMClient
from src.dd.adapters.zetaris_data_layer import ZetarisDataLayer, create_data_layer
from src.dd.config import Settings, get_settings


class TestGracefulDegradationFallbacks:
    """Verify system automatically falls back to DuckDB / Replay and marks degraded when live services fail."""

    def test_sample_mode_runs_offline_with_no_network(self) -> None:
        """SAMPLE_MODE=true must return local in-memory adapters with degraded=False."""
        dl, dl_degraded = asyncio.run(create_data_layer(sample_mode=True))
        llm, llm_degraded = asyncio.run(create_llm_client(sample_mode=True))

        assert isinstance(dl, DuckDBDataLayer)
        assert dl_degraded is False

        assert isinstance(llm, ReplayLLMClient)
        assert llm_degraded is False

    def test_zetaris_unreachable_triggers_duckdb_fallback(self) -> None:
        """When Zetaris host is unreachable, factory falls back to DuckDBDataLayer and flags degraded=True."""
        bad_settings = Settings(
            SAMPLE_MODE=False,
            ZETARIS_HOST="nonexistent.zetaris.invalid",
            ZETARIS_PORT=9999,
        )
        with patch("src.dd.adapters.zetaris_data_layer.get_settings", return_value=bad_settings):
            dl, is_degraded = asyncio.run(create_data_layer(sample_mode=False))
            assert isinstance(dl, DuckDBDataLayer)
            assert is_degraded is True

    def test_nightshift_unreachable_triggers_replay_fallback(self) -> None:
        """When Nightshift endpoint is unreachable, factory falls back to ReplayLLMClient and flags degraded=True."""
        bad_settings = Settings(
            SAMPLE_MODE=False,
            NIGHTSHIFT_BASE_URL="http://127.0.0.1:9999/v1",
            NIGHTSHIFT_API_KEY="valid-length-non-placeholder-test-key",
        )
        with patch("src.dd.adapters.nightshift_llm_client.get_settings", return_value=bad_settings):
            llm, is_degraded = asyncio.run(create_llm_client(sample_mode=False))
            assert isinstance(llm, ReplayLLMClient)
            assert is_degraded is True

    def test_nightshift_timeout_and_retry_config(self) -> None:
        """Verify 30-second timeout and 2-retry specifications are configured."""
        client = NightshiftLLMClient(
            base_url="http://localhost:8088/v1",
            api_key="test-key",
            timeout_sec=30.0,
            max_retries=2,
        )
        assert client.timeout_sec == 30.0
        assert client.max_retries == 2

    def test_nemotron_model_routing_per_agent(self) -> None:
        """Verify Red-team and Verifier use the Nemotron model, while Extractor uses the cheaper model."""
        client = NightshiftLLMClient(
            base_url="http://localhost:8088/v1",
            api_key="test-key",
        )
        settings = get_settings()

        assert client._get_model_for_agent("red_team") == settings.model_redteam
        assert client._get_model_for_agent("verifier") == settings.model_verifier
        assert client._get_model_for_agent("extractor") == settings.model_extractor
