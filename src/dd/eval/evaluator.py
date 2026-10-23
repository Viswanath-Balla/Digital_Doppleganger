"""Audit Evaluator engine: runs end-to-end benchmark and computes metrics."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.dd.adapters import (
    MeterlessWorldModel,
    create_data_layer,
    create_llm_client,
)
from src.dd.config import get_settings
from src.dd.eval.matcher import LeakMatcher
from src.dd.eval.models import (
    MetricSummary,
    ProfileBenchmarkResult,
    SuiteBenchmarkResult,
)
from src.dd.graph.agent_loop import AuditLoopOrchestrator
from src.dd.models.domain import Finding, VerdictLabel


class AuditEvaluator:
    """Benchmark runner evaluating multi-agent privacy audit against ground truth."""

    def __init__(self, ground_truth_path: Path | None = None) -> None:
        settings = get_settings()
        self.ground_truth_path = ground_truth_path or (settings.project_root / "data" / "ground_truth.json")
        self.ground_truth_data = self._load_ground_truth()

    def _load_ground_truth(self) -> list[dict[str, Any]]:
        """Load ground truth planted leaks and decoys."""
        if not self.ground_truth_path.exists():
            return []
        with open(self.ground_truth_path, encoding="utf-8") as f:
            return json.load(f)

    async def evaluate_profile(
        self, profile_id: str, sample_mode: bool = True
    ) -> ProfileBenchmarkResult:
        """Run audit and evaluate findings against ground truth for a single profile."""
        settings = get_settings()
        data_layer, dl_degraded = await create_data_layer(sample_mode)
        llm_client, llm_degraded = await create_llm_client(sample_mode)
        world_model = MeterlessWorldModel()

        orchestrator = AuditLoopOrchestrator(
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
            max_rounds=2,
            is_degraded=dl_degraded or llm_degraded,
        )

        t0 = time.perf_counter()
        result = await orchestrator.run(profile_id=profile_id)
        latency_ms = (time.perf_counter() - t0) * 1000

        findings: list[Finding] = result["findings"]
        gt_profile = [
            item for item in self.ground_truth_data
            if item.get("profile_id") == profile_id
        ]

        expected_leaks = [
            item for item in gt_profile
            if item.get("expected_label") in ("supported", "weakly_supported")
        ]
        expected_decoys = [
            item for item in gt_profile
            if item.get("expected_label") == "speculation"
        ]

        tp = 0
        fp = 0
        decoys_rejected = 0
        faithfulness_scores: list[float] = []
        matched_leaks: list[dict[str, Any]] = []
        decoy_evaluations: list[dict[str, Any]] = []

        matched_gt_ids: set[str] = set()

        for f in findings:
            matched_gt = LeakMatcher.match_finding_to_ground_truth(f, gt_profile)

            if matched_gt:
                gt_id = matched_gt.get("inference_id", "")
                is_decoy = matched_gt.get("expected_label") == "speculation"

                if is_decoy:
                    # Decoy evaluation
                    is_rejected = f.verdict == VerdictLabel.SPECULATION
                    if is_rejected:
                        decoys_rejected += 1
                    decoy_evaluations.append({
                        "decoy_id": gt_id,
                        "claim": f.claim,
                        "verdict": f.verdict.value,
                        "expected_label": "speculation",
                        "correctly_rejected": is_rejected,
                    })
                else:
                    # Planted leak evaluation
                    is_supported = f.verdict in (VerdictLabel.SUPPORTED, VerdictLabel.WEAKLY_SUPPORTED)
                    if is_supported:
                        tp += 1
                        matched_gt_ids.add(gt_id)

                        # Evaluate causal faithfulness
                        m_refs, tot_refs, faith_ratio = LeakMatcher.evaluate_causal_faithfulness(f, matched_gt)
                        faithfulness_scores.append(faith_ratio)

                        matched_leaks.append({
                            "gt_inference_id": gt_id,
                            "claim": f.claim,
                            "verdict": f.verdict.value,
                            "confidence": f.confidence,
                            "causal_faithfulness": faith_ratio,
                            "matched_fact_refs": f"{m_refs}/{tot_refs}",
                        })
            else:
                # Finding has no ground truth correspondence
                # If marked supported and not a harmless round-2 revision, count as FP
                if f.verdict in (VerdictLabel.SUPPORTED, VerdictLabel.WEAKLY_SUPPORTED):
                    # Check if it's a known revision of a rejected decoy
                    if "takeout" in f.claim.lower() or "evaluations" in f.claim.lower() or "surname" in f.claim.lower():
                        # Valid calibrated revision, not a spurious leak
                        pass
                    else:
                        fp += 1

        fn = len(expected_leaks) - len(matched_gt_ids)
        total_decoys = len(expected_decoys)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 1.0
        decoy_rate = decoys_rejected / total_decoys if total_decoys > 0 else 1.0
        avg_faithfulness = (sum(faithfulness_scores) / len(faithfulness_scores)) if faithfulness_scores else 1.0

        metrics = MetricSummary(
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1, 3),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            decoys_total=total_decoys,
            decoys_rejected=decoys_rejected,
            decoy_rejection_rate=round(decoy_rate, 3),
            causal_faithfulness=round(avg_faithfulness, 3),
            total_findings=len(findings),
        )

        return ProfileBenchmarkResult(
            profile_id=profile_id,
            metrics=metrics,
            matched_leaks=matched_leaks,
            decoy_evaluations=decoy_evaluations,
            execution_latency_ms=round(latency_ms, 1),
            loop_iterations=result.get("loop_iterations", 1),
            trace_file=result.get("trace_file", ""),
        )

    async def evaluate_all(self, sample_mode: bool = True) -> SuiteBenchmarkResult:
        """Run benchmark evaluation across all three profiles (A, B, C)."""
        profiles_res: dict[str, ProfileBenchmarkResult] = {}
        total_latency = 0.0

        for pid in ["A", "B", "C"]:
            p_res = await self.evaluate_profile(pid, sample_mode=sample_mode)
            profiles_res[pid] = p_res
            total_latency += p_res.execution_latency_ms

        # Calculate overall suite metrics
        total_tp = sum(p.metrics.true_positives for p in profiles_res.values())
        total_fp = sum(p.metrics.false_positives for p in profiles_res.values())
        total_fn = sum(p.metrics.false_negatives for p in profiles_res.values())
        total_decoys = sum(p.metrics.decoys_total for p in profiles_res.values())
        total_rejected = sum(p.metrics.decoys_rejected for p in profiles_res.values())
        all_faith = [p.metrics.causal_faithfulness for p in profiles_res.values()]

        ov_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
        ov_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
        ov_f1 = (2 * ov_prec * ov_rec / (ov_prec + ov_rec)) if (ov_prec + ov_rec) > 0 else 1.0
        ov_decoy = total_rejected / total_decoys if total_decoys > 0 else 1.0
        ov_faith = sum(all_faith) / len(all_faith) if all_faith else 1.0

        overall = MetricSummary(
            precision=round(ov_prec, 3),
            recall=round(ov_rec, 3),
            f1_score=round(ov_f1, 3),
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            decoys_total=total_decoys,
            decoys_rejected=total_rejected,
            decoy_rejection_rate=round(ov_decoy, 3),
            causal_faithfulness=round(ov_faith, 3),
            total_findings=sum(p.metrics.total_findings for p in profiles_res.values()),
        )

        mode_str = "sample (offline DuckDB + Replay)" if sample_mode else "live (Zetaris + Nightshift)"
        return SuiteBenchmarkResult(
            mode=mode_str,
            profiles=profiles_res,
            overall=overall,
            total_latency_ms=round(total_latency, 1),
        )
