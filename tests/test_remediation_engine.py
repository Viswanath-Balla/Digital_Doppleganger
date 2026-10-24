"""Automated tests for Phase 3 & Phase 4: Verifier Rubric, Essential Facts, and Remediation Engine."""

from __future__ import annotations

import asyncio
import pytest

from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer
from src.dd.adapters.meterless_world_model import MeterlessWorldModel
from src.dd.adapters.replay_llm_client import ReplayLLMClient
from src.dd.config import get_settings
from src.dd.graph.agent_loop import AuditLoopOrchestrator
from src.dd.models.domain import Finding, RiskLevel, VerdictLabel
from src.dd.remediation import (
    ActionType,
    RemediationCostModel,
    RemediationEngine,
)


class TestVerifierRubricAndEssentialFacts:
    """Validate Verifier rubric scores, essential_fact_ids, and threshold mappings."""

    def test_verifier_produces_essential_facts_and_rubric_scores(self) -> None:
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
        verdicts = result["verdicts"]
        assert len(verdicts) >= 4

        supported_verdicts = [v for v in verdicts if v.label == VerdictLabel.SUPPORTED]
        assert len(supported_verdicts) >= 2

        for sv in supported_verdicts:
            assert len(sv.essential_fact_ids) >= 1
            assert sv.total_score >= 7
            assert sv.score_factual_basis in (2, 3)
            assert sv.score_entailment in (2, 3)

        # Decoy check
        speculation_verdicts = [v for v in verdicts if v.label == VerdictLabel.SPECULATION]
        assert len(speculation_verdicts) >= 1
        for spv in speculation_verdicts:
            assert spv.total_score <= 3
            assert spv.essential_fact_ids == []
            assert spv.fix_request is not None


class TestCounterfactualRemediationEngine:
    """Validate deterministic causal collapse, cost model ranking, and exposure deltas."""

    def test_essential_fact_removal_causes_collapse(self) -> None:
        finding = Finding(
            profile_id="A",
            category="location",
            claim="Home address is 742 Evergreen Terr",
            verdict=VerdictLabel.SUPPORTED,
            essential_fact_ids=["fact_home_gps", "fact_delivery_addr"],
            min_independent_sources=2,
            evidence_chain=[
                {"_id": "fact_home_gps", "source_table": "strava_activities"},
                {"_id": "fact_delivery_addr", "source_table": "food_orders"},
            ],
        )

        # Removing an essential fact collapses the inference
        assert RemediationEngine.evaluate_collapse(finding, removed_fact_ids={"fact_home_gps"}) is True
        assert RemediationEngine.evaluate_collapse(finding, removed_fact_ids={"fact_delivery_addr"}) is True

    def test_non_essential_fact_removal_does_not_collapse(self) -> None:
        finding = Finding(
            profile_id="A",
            category="location",
            claim="Home address is 742 Evergreen Terr",
            verdict=VerdictLabel.SUPPORTED,
            essential_fact_ids=["fact_home_gps", "fact_delivery_addr"],
            min_independent_sources=2,
            evidence_chain=[
                {"_id": "fact_home_gps", "source_table": "strava_activities"},
                {"_id": "fact_delivery_addr", "source_table": "food_orders"},
                {"_id": "fact_random_post", "source_table": "social_posts"},
            ],
        )

        # Removing a non-essential fact leaves essential facts intact and min_sources satisfied
        assert RemediationEngine.evaluate_collapse(finding, removed_fact_ids={"fact_random_post"}) is False

    def test_independent_source_minimum_is_respected(self) -> None:
        finding = Finding(
            profile_id="A",
            category="location",
            claim="Multi-source corroboration required",
            verdict=VerdictLabel.SUPPORTED,
            essential_fact_ids=[],
            min_independent_sources=2,
            evidence_chain=[
                {"_id": "f1", "source_table": "strava_activities"},
                {"_id": "f2", "source_table": "food_orders"},
            ],
        )

        # Removing the whole source table reduces independent sources to 1 (< 2 required)
        assert RemediationEngine.evaluate_collapse(finding, removed_fact_ids=set(), removed_sources={"strava_activities"}) is True

    def test_cost_model_loads_from_config(self) -> None:
        assert RemediationCostModel.get_cost(ActionType.DELETE_POST) == 1
        assert RemediationCostModel.get_cost(ActionType.GENERALIZE_FIELD) == 1
        assert RemediationCostModel.get_cost(ActionType.CHANGE_RECOVERY_ANSWER) == 2
        assert RemediationCostModel.get_cost(ActionType.REMOVE_DATA_SOURCE) == 3

    def test_simulation_ranks_by_cost_efficiency_and_reduces_score(self) -> None:
        findings = [
            Finding(
                finding_id="fnd_1",
                profile_id="A",
                category="location",
                claim="Home address leak",
                verdict=VerdictLabel.SUPPORTED,
                risk_level=RiskLevel.HIGH,
                essential_fact_ids=["fact_gps"],
                min_independent_sources=2,
                evidence_chain=[
                    {"_id": "fact_gps", "source_table": "strava_activities", "value": "39.782, -89.65"},
                    {"_id": "fact_order", "source_table": "food_orders", "value": "742 Evergreen Terr"},
                ],
            ),
            Finding(
                finding_id="fnd_2",
                profile_id="A",
                category="routine",
                claim="Running routine leak",
                verdict=VerdictLabel.SUPPORTED,
                risk_level=RiskLevel.MODERATE,
                essential_fact_ids=["fact_gps"],  # fact_gps is a shared linchpin!
                min_independent_sources=1,
                evidence_chain=[
                    {"_id": "fact_gps", "source_table": "strava_activities", "value": "39.782, -89.65"},
                ],
            ),
        ]

        result = RemediationEngine.run_simulation("A", findings)

        assert result.exposure_before > 0
        assert result.exposure_after < result.exposure_before
        assert result.exposure_reduction > 0
        assert len(result.ranked_actions) >= 1

        # fact_gps should collapse both fnd_1 and fnd_2
        assert result.top_linchpin_fact_id == "fact_gps"
        assert result.top_linchpin_collapsed_chains == 2

        # Efficiency ranking: first action should have highest efficiency
        top_action = result.ranked_actions[0]
        assert top_action.efficiency >= result.ranked_actions[-1].efficiency
        assert top_action.what_to_do != ""
        assert top_action.why_it_helps != ""
        assert top_action.what_it_will_not_fix != ""

    @pytest.mark.parametrize("profile_id", ["A", "B", "C"])
    def test_all_profiles_produce_ranked_remediation_with_score_delta(
        self, profile_id: str
    ) -> None:
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

        result = asyncio.run(orchestrator.run(profile_id=profile_id))
        assert "remediation_plan" in result
        plan = result["remediation_plan"]

        assert plan.profile_id == profile_id
        assert plan.exposure_before > 0
        assert plan.exposure_after <= plan.exposure_before
        assert len(plan.ranked_actions) >= 1
