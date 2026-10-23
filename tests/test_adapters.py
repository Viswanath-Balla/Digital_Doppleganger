"""Tests for adapter interfaces and sample implementations."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.dd.adapters.sample_data_layer import SampleDataLayer
from src.dd.adapters.sample_llm_client import SampleLLMClient
from src.dd.adapters.sample_world_model import SampleWorldModel


# ---------------------------------------------------------------------------
# SampleDataLayer tests
# ---------------------------------------------------------------------------

class TestSampleDataLayer:
    """Verify the in-memory DataLayer implementation."""

    @pytest.fixture()
    def dl(self) -> SampleDataLayer:
        dl = SampleDataLayer()
        dl.load_table("users", [
            {"id": 1, "name": "Alice", "profile_id": "A"},
            {"id": 2, "name": "Bob", "profile_id": "B"},
        ])
        return dl

    def test_select_one(self, dl: SampleDataLayer) -> None:
        result = asyncio.get_event_loop().run_until_complete(dl.query("SELECT 1"))
        assert result == [{"1": 1}]

    def test_select_all_from_table(self, dl: SampleDataLayer) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            dl.query("SELECT * FROM users")
        )
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_select_with_where(self, dl: SampleDataLayer) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            dl.query("SELECT * FROM users WHERE profile_id = 'A'")
        )
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_select_with_limit(self, dl: SampleDataLayer) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            dl.query("SELECT * FROM users LIMIT 1")
        )
        assert len(result) == 1

    def test_health_check(self, dl: SampleDataLayer) -> None:
        assert asyncio.get_event_loop().run_until_complete(dl.health_check()) is True

    def test_invalid_sql_raises(self, dl: SampleDataLayer) -> None:
        with pytest.raises(ValueError, match="cannot parse"):
            asyncio.get_event_loop().run_until_complete(
                dl.query("DROP TABLE users")
            )


# ---------------------------------------------------------------------------
# SampleLLMClient tests
# ---------------------------------------------------------------------------

class TestSampleLLMClient:
    """Verify the stub LLM client."""

    def test_complete_returns_response(self) -> None:
        client = SampleLLMClient()
        resp = asyncio.get_event_loop().run_until_complete(
            client.complete(
                agent="red_team",
                messages=[{"role": "user", "content": "test prompt"}],
            )
        )
        assert resp.model == "sample-stub"
        assert "red_team" in resp.content
        assert resp.retries == 0
        assert resp.latency_ms >= 0

    def test_complete_echoes_last_user_message(self) -> None:
        client = SampleLLMClient()
        resp = asyncio.get_event_loop().run_until_complete(
            client.complete(
                agent="verifier",
                messages=[
                    {"role": "system", "content": "You are a verifier."},
                    {"role": "user", "content": "Check this claim."},
                ],
            )
        )
        assert "Check this claim" in resp.content


# ---------------------------------------------------------------------------
# SampleWorldModel tests
# ---------------------------------------------------------------------------

class TestSampleWorldModel:
    """Verify the in-memory World Model implementation."""

    @pytest.fixture()
    def wm(self) -> SampleWorldModel:
        return SampleWorldModel()

    def test_ingest_idempotent(self, wm: SampleWorldModel) -> None:
        """Ingesting the same data twice yields one entity with the same id."""
        id1 = wm.ingest("Fact", {"key": "home_address", "value": "123 Main St"}, "strava")
        id2 = wm.ingest("Fact", {"key": "home_address", "value": "123 Main St"}, "strava")
        assert id1 == id2
        # Only one entity exists
        all_facts = wm.query_entities("Fact")
        assert len(all_facts) == 1

    def test_ingest_different_data_different_ids(self, wm: SampleWorldModel) -> None:
        id1 = wm.ingest("Fact", {"key": "home", "value": "A"}, "src1")
        id2 = wm.ingest("Fact", {"key": "home", "value": "B"}, "src1")
        assert id1 != id2

    def test_ingest_same_data_different_source_keeps_provenance(self, wm: SampleWorldModel) -> None:
        """Two sources ingesting the same fact → one entity with both sources."""
        eid = wm.ingest("Fact", {"key": "city", "value": "NYC"}, "strava")
        wm.ingest("Fact", {"key": "city", "value": "NYC"}, "calendar")
        entity = wm.get(eid)
        assert entity is not None
        assert "strava" in entity["_sources"]
        assert "calendar" in entity["_sources"]

    def test_link_and_evidence_chain(self, wm: SampleWorldModel) -> None:
        """Evidence chain walks SUPPORTS edges back to source facts."""
        fact_id = wm.ingest("Fact", {"key": "addr", "value": "123 Main"}, "strava")
        inf_id = wm.ingest("Inference", {"claim": "lives at 123 Main"}, "red_team")
        wm.link(fact_id, inf_id, "SUPPORTS")

        chain = wm.evidence_chain(inf_id)
        assert len(chain) == 2
        # Leaf facts come first
        assert chain[0]["_id"] == fact_id
        assert chain[1]["_id"] == inf_id

    def test_query_entities_filtered(self, wm: SampleWorldModel) -> None:
        wm.ingest("Fact", {"key": "addr", "value": "A"}, "src1")
        wm.ingest("Fact", {"key": "phone", "value": "B"}, "src1")
        wm.ingest("Place", {"name": "NYC"}, "src1")

        facts = wm.query_entities("Fact")
        assert len(facts) == 2

        addr_facts = wm.query_entities("Fact", {"key": "addr"})
        assert len(addr_facts) == 1

    def test_get_nonexistent(self, wm: SampleWorldModel) -> None:
        assert wm.get("nonexistent") is None

    def test_link_nonexistent_raises(self, wm: SampleWorldModel) -> None:
        eid = wm.ingest("Fact", {"key": "a"}, "s")
        with pytest.raises(KeyError):
            wm.link(eid, "nonexistent", "SUPPORTS")


# ---------------------------------------------------------------------------
# Config / security tests
# ---------------------------------------------------------------------------

class TestConfig:
    """Verify configuration safety."""

    def test_sample_mode_defaults_true(self) -> None:
        from src.dd.config import get_settings
        settings = get_settings()
        assert settings.sample_mode is True

    def test_no_secrets_in_env_example(self) -> None:
        """Ensure .env.example contains only placeholders, not real keys."""
        env_example = Path(__file__).parent.parent / ".env.example"
        assert env_example.exists(), ".env.example not found"
        content = env_example.read_text()

        # Should not contain anything that looks like a real key
        # Real keys are typically 20+ chars of alphanumeric/special chars
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                _key, value = line.split("=", 1)
                value = value.strip()
                # Acceptable: empty, PLACEHOLDER_*, true/false, localhost, numbers, example URLs
                assert (
                    not value
                    or "PLACEHOLDER" in value.upper()
                    or "placeholder" in value
                    or "example.com" in value
                    or value.lower() in ("true", "false")
                    or value.replace(".", "").isdigit()
                    or value == "localhost"
                ), f"Suspicious value in .env.example: {line}"
