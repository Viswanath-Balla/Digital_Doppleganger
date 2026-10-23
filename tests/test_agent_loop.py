"""Tests for Phase 3: End-to-end agent loop, revision loops, and trace generation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer
from src.dd.adapters.meterless_world_model import MeterlessWorldModel
from src.dd.adapters.replay_llm_client import ReplayLLMClient
from src.dd.config import get_settings
from src.dd.graph.agent_loop import AuditLoopOrchestrator
from src.dd.models.domain import VerdictLabel


@pytest.fixture
def orchestrator() -> AuditLoopOrchestrator:
    settings = get_settings()
    data_layer = DuckDBDataLayer(sample_data_dir=settings.data_dir)
    world_model = MeterlessWorldModel()
    llm_client = ReplayLLMClient()

    return AuditLoopOrchestrator(
        world_model=world_model,
        data_layer=data_layer,
        llm_client=llm_client,
        max_rounds=2,
    )


class TestAgentLoopEndToEnd:
    """Verify end-to-end agent loop execution for Profile A in sample mode."""

    def test_profile_a_runs_and_produces_findings(
        self, orchestrator: AuditLoopOrchestrator
    ) -> None:
        result = asyncio.run(orchestrator.run(profile_id="A"))

        assert result is not None
        assert result["profile_id"] == "A"
        assert len(result["findings"]) >= 3
        assert len(result["verdicts"]) >= 3

    def test_decoy_ends_as_speculation(
        self, orchestrator: AuditLoopOrchestrator
    ) -> None:
        """The planted decoy 'works regular night shifts' must end as speculation."""
        result = asyncio.run(orchestrator.run(profile_id="A"))

        decoy_finding = next(
            (f for f in result["findings"] if "night shift" in f.claim.lower()),
            None,
        )
        assert decoy_finding is not None, "Decoy hypothesis not found in findings"
        assert decoy_finding.verdict == VerdictLabel.SPECULATION
        assert decoy_finding.confidence < 0.50

    def test_at_least_one_loop_iteration_occurs(
        self, orchestrator: AuditLoopOrchestrator
    ) -> None:
        """At least one inference must trigger an evidence request or rejection loop."""
        result = asyncio.run(orchestrator.run(profile_id="A"))
        assert result["loop_iterations"] >= 1, "Expected at least 1 feedback loop iteration"

    def test_loop_stops_at_configured_cap(
        self, orchestrator: AuditLoopOrchestrator
    ) -> None:
        """Loop must respect the max_rounds cap (2 rounds)."""
        result = asyncio.run(orchestrator.run(profile_id="A"))
        assert result["rounds_executed"] <= 2

    def test_trace_file_exists_and_contains_model_names(
        self, orchestrator: AuditLoopOrchestrator
    ) -> None:
        """JSONL trace must be written per run with logged model names."""
        result = asyncio.run(orchestrator.run(profile_id="A"))
        trace_path = Path(result["trace_file"])

        assert trace_path.exists(), f"Trace file {trace_path} not found"
        lines = trace_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 4, "Expected trace records for multiple agent steps"

        records = [json.loads(line) for line in lines]
        agent_names = {r["agent"] for r in records}
        assert {"planner", "extractor", "linker", "red_team", "verifier"}.issubset(
            agent_names
        )

        # Check that model names are recorded for LLM agents
        red_team_traces = [r for r in records if r["agent"] == "red_team"]
        assert len(red_team_traces) > 0
        assert "nemotron" in red_team_traces[0]["model"].lower() or "stub" in red_team_traces[0]["model"].lower()

        verifier_traces = [r for r in records if r["agent"] == "verifier"]
        assert len(verifier_traces) > 0
        assert "nemotron" in verifier_traces[0]["model"].lower() or "stub" in verifier_traces[0]["model"].lower()

    def test_evidence_chains_grounded_to_source_rows(
        self, orchestrator: AuditLoopOrchestrator
    ) -> None:
        """Supported findings must have multi-step evidence chains rooted in source facts."""
        result = asyncio.run(orchestrator.run(profile_id="A"))

        home_finding = next(
            (f for f in result["findings"] if "home address" in f.claim.lower()),
            None,
        )
        assert home_finding is not None
        assert home_finding.verdict == VerdictLabel.SUPPORTED
        assert len(home_finding.evidence_chain) >= 2

        # Check that source tables are present in the chain
        source_tables = {
            node.get("source_table")
            for node in home_finding.evidence_chain
            if "source_table" in node
        }
        assert "food_orders" in source_tables or "strava_activities" in source_tables
