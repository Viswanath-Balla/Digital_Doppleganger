"""Automated tests for Phase 6: Evaluation Harness & Benchmark Suite."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.dd.eval.evaluator import AuditEvaluator
from src.dd.eval.matcher import LeakMatcher
from src.dd.eval.models import (
    MetricSummary,
    ProfileBenchmarkResult,
    SuiteBenchmarkResult,
)
from src.dd.eval.reporter import EvalReporter
from src.dd.models.domain import Finding, VerdictLabel


class TestLeakMatcher:
    """Validate semantic ground truth matching and causal attribution."""

    def test_match_known_findings(self) -> None:
        gt_items = [
            {"inference_id": "A_INF_HOME_ADDR", "claim": "Home address is 742 Evergreen Terr"},
            {"inference_id": "A_INF_DECOY_NIGHTSHIFT", "claim": "Works regular night shifts"},
        ]
        f1 = Finding(
            profile_id="A",
            category="location",
            claim="Home address is 742 Evergreen Terr, Springfield",
            verdict=VerdictLabel.SUPPORTED,
        )
        f2 = Finding(
            profile_id="A",
            category="employment",
            claim="Works regular night shifts as primary employment",
            verdict=VerdictLabel.SPECULATION,
        )

        m1 = LeakMatcher.match_finding_to_ground_truth(f1, gt_items)
        assert m1 is not None
        assert m1["inference_id"] == "A_INF_HOME_ADDR"

        m2 = LeakMatcher.match_finding_to_ground_truth(f2, gt_items)
        assert m2 is not None
        assert m2["inference_id"] == "A_INF_DECOY_NIGHTSHIFT"

    def test_unmatched_claim_returns_none(self) -> None:
        gt_items = [
            {"inference_id": "A_INF_HOME_ADDR", "claim": "Home address is 742 Evergreen Terr"},
        ]
        f_unknown = Finding(
            profile_id="A",
            category="random",
            claim="Owns an exotic sports car in Italy",
            verdict=VerdictLabel.SUPPORTED,
        )
        assert LeakMatcher.match_finding_to_ground_truth(f_unknown, gt_items) is None

    def test_causal_faithfulness_scoring(self) -> None:
        gt_item = {
            "required_fact_refs": [
                {"table": "food_orders", "key_col": "delivery_address", "value": "742 Evergreen Terr"},
                {"table": "strava_activities", "key_col": "start_lat", "value": "39.7817"},
            ]
        }
        finding = Finding(
            profile_id="A",
            category="location",
            claim="Home address",
            verdict=VerdictLabel.SUPPORTED,
            evidence_chain=[
                {"_type": "Fact", "source_table": "food_orders", "delivery_address": "742 Evergreen Terr"},
                {"_type": "Fact", "source_table": "strava_activities", "start_lat": 39.7817},
            ],
        )
        matched, total, ratio = LeakMatcher.evaluate_causal_faithfulness(finding, gt_item)
        assert matched == 2
        assert total == 2
        assert ratio == 1.0


class TestAuditEvaluator:
    """Validate end-to-end benchmark evaluation against synthetic ground truth."""

    def test_evaluate_profile_a_metrics(self) -> None:
        evaluator = AuditEvaluator()
        res = asyncio.run(evaluator.evaluate_profile("A", sample_mode=True))

        assert res.profile_id == "A"
        assert res.metrics.precision == 1.0
        assert res.metrics.recall == 1.0
        assert res.metrics.f1_score == 1.0
        assert res.metrics.decoy_rejection_rate == 1.0
        assert res.metrics.decoys_rejected == 1
        assert res.metrics.causal_faithfulness >= 0.90

    def test_evaluate_full_suite_benchmark(self) -> None:
        evaluator = AuditEvaluator()
        suite = asyncio.run(evaluator.evaluate_all(sample_mode=True))

        assert len(suite.profiles) == 3
        # Assert rigorous benchmark thresholds
        assert suite.overall.precision >= 0.95
        assert suite.overall.recall >= 0.95
        assert suite.overall.f1_score >= 0.95
        assert suite.overall.decoy_rejection_rate == 1.0
        assert suite.overall.decoys_rejected == 3
        assert suite.overall.causal_faithfulness >= 0.90


class TestEvalReporter:
    """Validate scoreboard formatting and report artifact writing."""

    def test_format_terminal_table(self) -> None:
        p_res = ProfileBenchmarkResult(
            profile_id="A",
            metrics=MetricSummary(
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
                decoys_total=1,
                decoys_rejected=1,
                decoy_rejection_rate=1.0,
                causal_faithfulness=1.0,
            ),
            execution_latency_ms=120.0,
        )
        suite = SuiteBenchmarkResult(
            mode="sample",
            profiles={"A": p_res},
            overall=p_res.metrics,
            total_latency_ms=120.0,
        )
        table = EvalReporter.format_terminal_table(suite)
        assert "BENCHMARK SUITE" in table
        assert "A (Runner)" in table
        assert "OVERALL SUITE" in table
        assert "100.0%" in table

    def test_save_benchmark_artifacts(self, tmp_path: Path) -> None:
        p_res = ProfileBenchmarkResult(
            profile_id="A",
            metrics=MetricSummary(),
        )
        suite = SuiteBenchmarkResult(
            mode="sample",
            profiles={"A": p_res},
            overall=MetricSummary(),
        )
        json_path, md_path = EvalReporter.save_benchmark_artifacts(suite, tmp_path)

        assert json_path.exists()
        assert md_path.exists()

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["suite_name"] == "Digital Doppelgänger Evaluation Harness"

        md_text = md_path.read_text(encoding="utf-8")
        assert "Evaluation Harness & Benchmark Results" in md_text
        assert "Decoy Rejection Proof" in md_text
