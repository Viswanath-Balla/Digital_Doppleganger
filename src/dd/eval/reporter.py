"""Benchmark reporter: terminal table formatting and Markdown/JSON artifact export."""

from __future__ import annotations

import json
from pathlib import Path

from src.dd.eval.models import SuiteBenchmarkResult


class EvalReporter:
    """Formats and exports benchmark evaluation reports."""

    @classmethod
    def format_terminal_table(cls, suite: SuiteBenchmarkResult) -> str:
        """Render a clean, formatted ASCII scoreboard for terminal display."""
        lines = []
        lines.append("=" * 96)
        lines.append(" DIGITAL DOPPELGÄNGER BENCHMARK SUITE: EVALUATION HARNESS")
        lines.append(f" Mode: {suite.mode} | Timestamp: {suite.timestamp_utc}")
        lines.append("=" * 96)
        lines.append(
            f" {'Profile':<14} | {'Precision':<9} | {'Recall':<9} | {'F1':<6} | {'Decoy Rej.':<12} | {'Faithfulness':<12} | {'Latency':<8}"
        )
        lines.append("-" * 96)

        persona_names = {
            "A": "A (Runner)",
            "B": "B (Corporate)",
            "C": "C (Creator)",
        }

        for pid, pres in suite.profiles.items():
            m = pres.metrics
            p_name = persona_names.get(pid, f"Profile {pid}")
            decoy_str = f"{m.decoy_rejection_rate * 100:.0f}% ({m.decoys_rejected}/{m.decoys_total})"
            lines.append(
                f" {p_name:<14} | {m.precision * 100:>8.1f}% | {m.recall * 100:>8.1f}% | {m.f1_score:>6.3f} | {decoy_str:<12} | {m.causal_faithfulness * 100:>11.1f}% | {pres.execution_latency_ms / 1000:>6.2f}s"
            )

        lines.append("-" * 96)
        ov = suite.overall
        ov_decoy_str = f"{ov.decoy_rejection_rate * 100:.0f}% ({ov.decoys_rejected}/{ov.decoys_total})"
        lines.append(
            f" {'OVERALL SUITE':<14} | {ov.precision * 100:>8.1f}% | {ov.recall * 100:>8.1f}% | {ov.f1_score:>6.3f} | {ov_decoy_str:<12} | {ov.causal_faithfulness * 100:>11.1f}% | {suite.total_latency_ms / 1000:>6.2f}s"
        )
        lines.append("=" * 96)
        return "\n".join(lines)

    @classmethod
    def generate_markdown_summary(cls, suite: SuiteBenchmarkResult) -> str:
        """Render a GitHub-flavored Markdown evaluation summary report."""
        ov = suite.overall
        md = []
        md.append("# Digital Doppelgänger: Evaluation Harness & Benchmark Results")
        md.append(f"**Benchmark Mode:** `{suite.mode}` | **Timestamp:** {suite.timestamp_utc}")
        md.append(f"**Total Suite Latency:** `{suite.total_latency_ms:.1f}ms` ({suite.total_latency_ms / 1000:.2f}s)\n")
        md.append("---\n")

        md.append("## 1. Executive Benchmark Summary\n")
        md.append(
            f"> **OVERALL F1-SCORE: {ov.f1_score:.3f} | DECOY REJECTION RATE: {ov.decoy_rejection_rate * 100:.0f}% | CAUSAL FAITHFULNESS: {ov.causal_faithfulness * 100:.1f}%**\n"
        )

        md.append("| Target Persona | Precision | Recall | F1-Score | Decoy Rejection Rate | Causal Attribution Faithfulness | Execution Latency |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for pid, pres in suite.profiles.items():
            m = pres.metrics
            decoy_str = f"{m.decoy_rejection_rate * 100:.0f}% ({m.decoys_rejected}/{m.decoys_total})"
            md.append(
                f"| **Profile {pid}** | {m.precision * 100:.1f}% | {m.recall * 100:.1f}% | {m.f1_score:.3f} | {decoy_str} | {m.causal_faithfulness * 100:.1f}% | {pres.execution_latency_ms / 1000:.2f}s |"
            )

        ov_decoy_str = f"{ov.decoy_rejection_rate * 100:.0f}% ({ov.decoys_rejected}/{ov.decoys_total})"
        md.append(
            f"| **OVERALL** | **{ov.precision * 100:.1f}%** | **{ov.recall * 100:.1f}%** | **{ov.f1_score:.3f}** | **{ov_decoy_str}** | **{ov.causal_faithfulness * 100:.1f}%** | **{suite.total_latency_ms / 1000:.2f}s** |\n"
        )

        md.append("## 2. Decoy Rejection Proof ('The Agent That Can Explain Why')\n")
        md.append(
            "A core capability evaluated in Track 2 is whether the Verifier Agent can resist hasty generalizations "
            "and ungrounded planted decoys. All planted decoys must end strictly as `speculation`.\n"
        )
        md.append("| Profile | Planted Decoy Claim | Verifier Verdict | Expected Verdict | Rejection Status |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")

        for pid, pres in suite.profiles.items():
            for dec in pres.decoy_evaluations:
                status_icon = "PASSED" if dec["correctly_rejected"] else "FAILED"
                md.append(
                    f"| Profile {pid} | {dec['claim']} | `{dec['verdict']}` | `{dec['expected_label']}` | **{status_icon}** |"
                )
        md.append("\n---\n")

        md.append("## 3. Grounded Causal Attribution Verification\n")
        md.append(
            "Verifies that the evidence chains produced by the World Model and tested by the Counterfactual Engine "
            "faithfully capture the true planted ground-truth fact references.\n"
        )
        md.append("| Profile | Corroborated Leak | Ground-Truth ID | Matched Fact References | Causal Faithfulness |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")

        for pid, pres in suite.profiles.items():
            for leak in pres.matched_leaks:
                md.append(
                    f"| Profile {pid} | {leak['claim']} | `{leak['gt_inference_id']}` | {leak['matched_fact_refs']} | **{leak['causal_faithfulness'] * 100:.1f}%** |"
                )

        return "\n".join(md)

    @classmethod
    def save_benchmark_artifacts(
        cls, suite: SuiteBenchmarkResult, reports_dir: Path
    ) -> tuple[Path, Path]:
        """Save benchmark JSON and Markdown summary to reports directory."""
        reports_dir.mkdir(parents=True, exist_ok=True)

        json_path = reports_dir / "eval_benchmark_results.json"
        md_path = reports_dir / "eval_benchmark_summary.md"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(suite.model_dump(), f, indent=2)

        md_content = cls.generate_markdown_summary(suite)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return json_path, md_path
