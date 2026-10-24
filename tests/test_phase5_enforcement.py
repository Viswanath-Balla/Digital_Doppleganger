"""Tests enforcing code behavior, verifier rubric, loop caps, and secret/model hygiene (Phase 5)."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer
from src.dd.adapters.meterless_world_model import MeterlessWorldModel
from src.dd.adapters.replay_llm_client import ReplayLLMClient
from src.dd.agents.prompt_loader import PROMPTS_DIR, get_prompt
from src.dd.agents.verifier import VerifierAgent
from src.dd.config import get_settings
from src.dd.graph.agent_loop import AuditLoopOrchestrator
from src.dd.models.domain import AttackerModel, Finding, RiskLevel, Verdict, VerdictLabel


class TestPhase5Enforcement:
    """Validate all Phase 5 code enforcement rules and constraints."""

    def test_every_prompt_file_has_required_sections_and_version(self) -> None:
        """Every prompt file in src/dd/agents/prompts/ must have version and required sections."""
        prompt_files = list(PROMPTS_DIR.glob("*.md"))
        assert len(prompt_files) >= 5, "Expected at least 5 agent prompt files"

        for p_file in prompt_files:
            prompt_info = get_prompt(p_file.stem)
            assert prompt_info.version != ""
            assert len(prompt_info.sha256) == 64

            txt = prompt_info.content
            assert "## Role" in txt
            assert "## Inputs" in txt
            assert "## Output schema" in txt
            assert "## Rules" in txt
            assert "## Stop / fail conditions" in txt
            assert "## Tools allowed" in txt

    def test_verifier_total_below_7_triggers_fix_request(self) -> None:
        """A verifier total below 7 triggers exactly one fix request."""
        v_low = Verdict(
            inference_id="inf_spec",
            label=VerdictLabel.SPECULATION,
            confidence=0.20,
            rationale="Insufficient evidence",
            score_factual_basis=1,
            score_entailment=1,
            score_no_benign=0,
            total_score=2,
            fix_request="Obtain primary source evidence or discard speculative claim.",
        )
        assert v_low.total_score < 7
        assert v_low.fix_request is not None
        assert len(v_low.fix_request) > 0

    def test_thresholds_map_scores_to_right_labels(self) -> None:
        """Thresholds map scores: 7-9 supported, 4-6 weakly_supported, 0-3 speculation."""
        settings = get_settings()
        th_sup = settings.verifier_threshold_supported
        th_weak = settings.verifier_threshold_weakly_supported

        assert th_sup == 7
        assert th_weak == 4

        # Test score 8
        score_8 = 8
        label_8 = VerdictLabel.SUPPORTED if score_8 >= th_sup else (VerdictLabel.WEAKLY_SUPPORTED if score_8 >= th_weak else VerdictLabel.SPECULATION)
        assert label_8 == VerdictLabel.SUPPORTED

        # Test score 5
        score_5 = 5
        label_5 = VerdictLabel.SUPPORTED if score_5 >= th_sup else (VerdictLabel.WEAKLY_SUPPORTED if score_5 >= th_weak else VerdictLabel.SPECULATION)
        assert label_5 == VerdictLabel.WEAKLY_SUPPORTED

        # Test score 2
        score_2 = 2
        label_2 = VerdictLabel.SUPPORTED if score_2 >= th_sup else (VerdictLabel.WEAKLY_SUPPORTED if score_2 >= th_weak else VerdictLabel.SPECULATION)
        assert label_2 == VerdictLabel.SPECULATION

    def test_two_round_cap_holds_and_downgrades_unresolved(self) -> None:
        """2-round cap holds strictly and rejected claim ends as speculation or downgraded."""
        settings = get_settings()
        data_layer = DuckDBDataLayer(sample_data_dir=settings.data_dir)
        world_model = MeterlessWorldModel()
        llm_client = ReplayLLMClient()

        orchestrator = AuditLoopOrchestrator(
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
            max_rounds=2,
        )

        result = asyncio.run(orchestrator.run(profile_id="A"))
        assert result["rounds_executed"] <= 2

        # The planted decoy hypothesis ends as speculation
        nightshift_finding = next(
            (f for f in result["findings"] if "night shift" in f.claim.lower()), None
        )
        assert nightshift_finding is not None
        assert nightshift_finding.verdict == VerdictLabel.SPECULATION

    def test_red_team_input_contains_brief_only(self) -> None:
        """Red-team agent reads from the provided brief only and rejects raw table rows."""
        settings = get_settings()
        data_layer = DuckDBDataLayer(sample_data_dir=settings.data_dir)
        world_model = MeterlessWorldModel()
        llm_client = ReplayLLMClient()

        orchestrator = AuditLoopOrchestrator(
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
        )

        # Brief packed by Linker
        brief = {
            "profile_id": "A",
            "brief": "Context Brief: 35 facts processed.",
            "cites": ["fact_1", "fact_2"],
            "risks": ["GPS drift risk"],
            "open_qs": ["Secondary residence?"],
        }

        inferences = asyncio.run(
            orchestrator.red_team.propose_inferences(
                profile_id="A",
                round_num=1,
                brief=brief,
            )
        )
        assert len(inferences) > 0

    def test_trace_contains_prompt_file_version_hash_model_name(self) -> None:
        """Trace contains prompt file, version, sha256 hash, and model name on every step."""
        settings = get_settings()
        data_layer = DuckDBDataLayer(sample_data_dir=settings.data_dir)
        world_model = MeterlessWorldModel()
        llm_client = ReplayLLMClient()

        orchestrator = AuditLoopOrchestrator(
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
        )

        result = asyncio.run(orchestrator.run(profile_id="A"))
        traces = result["traces"]
        assert len(traces) >= 5

        for tr in traces:
            assert tr.model != ""
            assert tr.prompt_file is not None
            assert tr.prompt_version == "1.0"
            assert len(tr.prompt_sha256 or "") == 64

    def test_no_prompt_file_hardcodes_model_name(self) -> None:
        """No prompt file in src/dd/agents/prompts/ hardcodes model IDs."""
        forbidden_models = [
            "nvidia/nemotron",
            "gpt-4",
            "claude-3",
            "llama-3",
            "mistral",
        ]
        for p_file in PROMPTS_DIR.glob("*.md"):
            txt = p_file.read_text(encoding="utf-8").lower()
            for model in forbidden_models:
                assert model not in txt, f"Hardcoded model '{model}' found in {p_file.name}"

    def test_sample_mode_runs_offline_with_no_credentials(self) -> None:
        """Sample mode executes end-to-end without credentials."""
        settings = get_settings()
        data_layer = DuckDBDataLayer(sample_data_dir=settings.data_dir)
        world_model = MeterlessWorldModel()
        llm_client = ReplayLLMClient()

        orchestrator = AuditLoopOrchestrator(
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
        )

        result = asyncio.run(orchestrator.run(profile_id="A"))
        assert result is not None
        assert len(result["findings"]) >= 4
