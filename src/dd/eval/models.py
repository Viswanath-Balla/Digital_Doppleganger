"""Data models for evaluation harness and benchmark metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class MetricSummary(BaseModel):
    """Core detection, decoy rejection, and causal attribution metrics."""

    precision: float = 1.0
    recall: float = 1.0
    f1_score: float = 1.0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    decoys_total: int = 0
    decoys_rejected: int = 0
    decoy_rejection_rate: float = 1.0
    causal_faithfulness: float = 1.0  # % of ground truth required facts in evidence chain
    total_findings: int = 0


class ProfileBenchmarkResult(BaseModel):
    """Benchmark results for an individual persona (Profile A, B, or C)."""

    profile_id: str
    metrics: MetricSummary
    matched_leaks: list[dict[str, Any]] = Field(default_factory=list)
    decoy_evaluations: list[dict[str, Any]] = Field(default_factory=list)
    execution_latency_ms: float = 0.0
    loop_iterations: int = 1
    trace_file: str = ""


class SuiteBenchmarkResult(BaseModel):
    """Aggregate benchmark results across the complete profile suite."""

    suite_name: str = "Digital Doppelgänger Evaluation Harness"
    timestamp_utc: str = Field(default_factory=_utc_now_str)
    mode: str = "sample"
    profiles: dict[str, ProfileBenchmarkResult] = Field(default_factory=dict)
    overall: MetricSummary
    total_latency_ms: float = 0.0
