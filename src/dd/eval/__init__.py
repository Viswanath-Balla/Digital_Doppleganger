"""Evaluation Harness and Benchmarking Package for Digital Doppelgänger."""

from src.dd.eval.evaluator import AuditEvaluator
from src.dd.eval.models import (
    MetricSummary,
    ProfileBenchmarkResult,
    SuiteBenchmarkResult,
)

__all__ = [
    "AuditEvaluator",
    "MetricSummary",
    "ProfileBenchmarkResult",
    "SuiteBenchmarkResult",
]
