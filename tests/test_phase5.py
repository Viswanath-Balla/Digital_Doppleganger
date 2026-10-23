"""Tests for Phase 5: Risk Scoring, Counterfactual Engine, Remediation, and Reports."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer
from src.dd.adapters.meterless_world_model import MeterlessWorldModel
from src.dd.adapters.replay_llm_client import ReplayLLMClient
from src.dd.analysis import (
    CounterfactualRemovalEngine,
    RemediationGenerator,
    RiskScorer,
)
from src.dd.config import get_settings
from src.dd.graph.agent_loop import AuditLoopOrchestrator
from src.dd.models.domain import (
    AttackerModel,
    Finding,
    RiskLevel,
    VerdictLabel,
)
from src.dd.reporting import ReportGenerator


class TestRiskScorer:
    """Validate L1-L5 severity taxonomy, threat models, and exposure index."""

    def test_speculation_scored_informational(self) -> None:
        finding = Finding(
            profile_id="A",
            category="employment",
            claim="Works night shifts",
            verdict=VerdictLabel.SPECULATION,
            confidence=0.20,
        )
        scored = RiskScorer.score_finding(finding)
        assert scored.risk_level == RiskLevel.INFORMATIONAL
        assert AttackerModel.BURGLAR in scored.attacker_models or AttackerModel.EMPLOYER in scored.attacker_models

    def test_location_supported_scored_high(self) -> None:
        finding = Finding(
            profile_id="A",
            category="location",
            claim="Home address is 742 Evergreen Terr",
            verdict=VerdictLabel.SUPPORTED,
            confidence=0.95,
        )
        scored = RiskScorer.score_finding(finding)
        assert scored.risk_level == RiskLevel.HIGH
        assert AttackerModel.STALKER in scored.attacker_models
        assert AttackerModel.BURGLAR in scored.attacker_models

    def test_composite_exposure_index_calculation(self) -> None:
        findings = [
            Finding(
                profile_id="A",
                category="location",
                claim="Home address",
                verdict=VerdictLabel.SUPPORTED,
                confidence=0.95,
                risk_level=RiskLevel.HIGH,
            ),
            Finding(
                profile_id="A",
                category="routine",
                claim="Running routine",
                verdict=VerdictLabel.SUPPORTED,
                confidence=0.90,
                risk_level=RiskLevel.MODERATE,
            ),
            Finding(
                profile_id="A",
                category="employment",
                claim="Night shifts",
                verdict=VerdictLabel.SPECULATION,
                confidence=0.20,
                risk_level=RiskLevel.INFORMATIONAL,
            ),
        ]
        summary = RiskScorer.compute_exposure_summary(findings)
        assert summary["exposure_score"] > 0
        assert summary["exposure_score"] <= 100
        assert summary["exposure_tier"] in ("HIGH", "MODERATE", "CRITICAL")
        assert summary["level_counts"]["HIGH"] == 1
        assert summary["level_counts"]["MODERATE"] == 1
        assert summary["level_counts"]["INFORMATIONAL"] == 1


class TestCounterfactualEngine:
    """Validate causal collapse proofs upon leaf fact excision."""

    def test_speculation_returns_no_collapse_needed(self) -> None:
        finding = Finding(
            profile_id="A",
            category="employment",
            claim="Works night shifts",
            verdict=VerdictLabel.SPECULATION,
            confidence=0.20,
        )
        res = CounterfactualRemovalEngine.evaluate_finding(finding)
        assert res["collapse_proved"] is False
        assert len(res["linchpin_facts"]) == 0

    def test_supported_finding_identifies_linchpin_and_proves_collapse(self) -> None:
        finding = Finding(
            profile_id="A",
            category="location",
            claim="Home address is 742 Evergreen Terr",
            verdict=VerdictLabel.SUPPORTED,
            confidence=0.95,
            evidence_chain=[
                {"_type": "Fact", "_id": "fact_13c_coord", "source_table": "strava_activities", "value": "39.782, -89.65"},
                {"_type": "Fact", "_id": "fact_a40_addr", "source_table": "food_orders", "value": "742 Evergreen Terr"},
                {"_type": "Place", "_id": "plac_home", "name": "Home Residence"},
            ],
        )
        res = CounterfactualRemovalEngine.evaluate_finding(finding)
        assert res["collapse_proved"] is True
        assert len(res["linchpin_facts"]) >= 1
        assert len(res["excision_results"]) >= 2
        # Verify drop to 0%
        first_ex = res["excision_results"][0]
        assert first_ex["post_removal_confidence"] == 0.0
        assert "Causal Collapse Verified" in res["summary_explanation"]


class TestRemediationGenerator:
    """Validate targeted action synthesis."""

    def test_remediation_generation(self) -> None:
        finding = Finding(
            profile_id="A",
            category="location",
            claim="Home address is 742 Evergreen Terr",
            verdict=VerdictLabel.SUPPORTED,
            risk_level=RiskLevel.HIGH,
        )
        rem = RemediationGenerator.generate_remediation(finding)
        assert "Privacy Zones" in rem["title"]
        assert "Immediate" in rem["priority"]
        assert len(rem["steps"]) >= 2
        assert finding.remediation != ""


class TestReportGenerator:
    """Validate Markdown and JSON export formatting."""

    def test_report_generation_and_export(self, tmp_path: Path) -> None:
        findings = [
            Finding(
                profile_id="A",
                category="location",
                claim="Home address",
                verdict=VerdictLabel.SUPPORTED,
                confidence=0.95,
                risk_level=RiskLevel.HIGH,
                evidence_chain=[
                    {"_type": "Fact", "_id": "f1", "value": "39.782, -89.65"},
                    {"_type": "Place", "_id": "p1", "name": "Home Residence"},
                ],
            )
        ]
        exposure_summary = RiskScorer.compute_exposure_summary(findings)
        cf_evals = CounterfactualRemovalEngine.evaluate_all(findings)
        remediations = RemediationGenerator.apply_all(findings)

        md_path, json_path = ReportGenerator.save_reports(
            reports_dir=tmp_path,
            profile_id="A",
            findings=findings,
            exposure_summary=exposure_summary,
            counterfactual_evals=cf_evals,
            remediation_plans=remediations,
            trace_file="test_trace.jsonl",
        )

        assert md_path.exists()
        assert json_path.exists()

        md_text = md_path.read_text(encoding="utf-8")
        assert "PRIVACY EXPOSURE INDEX" in md_text
        assert "mermaid" in md_text
        assert "Causal Explanation" in md_text

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["audit_schema_version"] == "1.0.0"
        assert len(data["findings"]) == 1


class TestMultiProfileAudits:
    """Ensure end-to-end audits succeed across Profiles A, B, and C with decoys rejected."""

    def _build_orchestrator(self) -> AuditLoopOrchestrator:
        settings = get_settings()
        return AuditLoopOrchestrator(
            world_model=MeterlessWorldModel(),
            data_layer=DuckDBDataLayer(sample_data_dir=settings.data_dir),
            llm_client=ReplayLLMClient(),
            max_rounds=2,
        )

    def test_profile_b_audit_and_decoy_rejection(self) -> None:
        orch = self._build_orchestrator()
        result = asyncio.run(orch.run(profile_id="B"))

        assert len(result["findings"]) >= 3
        # Oncology specialist visit should be supported
        onco = next((f for f in result["findings"] if "oncology" in f.claim.lower()), None)
        assert onco is not None
        assert onco.verdict == VerdictLabel.SUPPORTED

        # Lymphoma clinical diagnosis must be rejected as speculation
        decoy = next((f for f in result["findings"] if "lymphoma" in f.claim.lower()), None)
        assert decoy is not None
        assert decoy.verdict == VerdictLabel.SPECULATION

    def test_profile_c_audit_and_decoy_rejection(self) -> None:
        orch = self._build_orchestrator()
        result = asyncio.run(orch.run(profile_id="C"))

        assert len(result["findings"]) >= 3
        # DOB and pet dog should be supported
        dob = next((f for f in result["findings"] if "1996" in f.claim.lower()), None)
        assert dob is not None
        assert dob.verdict == VerdictLabel.SUPPORTED

        pet = next((f for f in result["findings"] if "barnaby" in f.claim.lower()), None)
        assert pet is not None
        assert pet.verdict == VerdictLabel.SUPPORTED

        # Mother's maiden name Vance must be rejected as speculation
        decoy = next((f for f in result["findings"] if "vance" in f.claim.lower()), None)
        assert decoy is not None
        assert decoy.verdict == VerdictLabel.SPECULATION
