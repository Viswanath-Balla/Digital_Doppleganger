"""Digital Doppelgänger — main entrypoint.

Runs the multi-agent privacy audit end-to-end for a given profile.
Usage: python -m src.dd.main --profile A
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.dd.adapters import (
    MeterlessWorldModel,
    create_data_layer,
    create_llm_client,
)
from src.dd.analysis import (
    CounterfactualRemovalEngine,
    RemediationGenerator,
    RiskScorer,
)
from src.dd.config import get_settings
from src.dd.graph.agent_loop import AuditLoopOrchestrator
from src.dd.reporting import ReportGenerator


async def run_audit(profile_id: str, sample_mode: bool | None = None) -> None:
    settings = get_settings()
    is_sample = sample_mode if sample_mode is not None else settings.sample_mode
    data_layer, dl_degraded = await create_data_layer(is_sample)
    llm_client, llm_degraded = await create_llm_client(is_sample)
    world_model = MeterlessWorldModel()

    is_degraded = dl_degraded or llm_degraded

    mode_label = "SAMPLE" if is_sample else "LIVE"
    if is_degraded:
        mode_label += " [DEGRADED: Fallback Active]"

    dl_name = "ZetarisDataLayer" if hasattr(data_layer, "database") else "DuckDBDataLayer"
    llm_name = type(llm_client).__name__

    print("=" * 70)
    print(" DIGITAL DOPPELGANGER -- Multi-Agent Privacy Audit")
    print(f" Mode:       {mode_label}")
    print(f" Data Layer: {dl_name}")
    print(f" LLM Client: {llm_name}")
    print(f" Profile:    {profile_id}")
    print("=" * 70)

    # Build and execute the orchestrator
    orchestrator = AuditLoopOrchestrator(
        world_model=world_model,
        data_layer=data_layer,
        llm_client=llm_client,
        max_rounds=2,
        is_degraded=is_degraded,
    )

    print("\n[dd] Starting agent loop: Planner -> Extractor -> Linker -> Red-Team <-> Verifier...")
    result = await orchestrator.run(profile_id=profile_id)
    findings = result["findings"]

    # --- Phase 5: Risk Scoring, Counterfactual Proofs & Remediation ---
    exposure_summary = RiskScorer.compute_exposure_summary(findings)
    counterfactual_evals = CounterfactualRemovalEngine.evaluate_all(findings)
    remediation_plans = RemediationGenerator.apply_all(findings)

    # Export Dual Reports (Markdown + JSON)
    reports_dir = settings.project_root / "reports"
    md_path, json_path = ReportGenerator.save_reports(
        reports_dir=reports_dir,
        profile_id=profile_id,
        findings=findings,
        exposure_summary=exposure_summary,
        counterfactual_evals=counterfactual_evals,
        remediation_plans=remediation_plans,
        trace_file=result["trace_file"],
    )

    # 3. Pretty-print findings and verdicts
    print("\n" + "=" * 70)
    print(f" AUDIT FINDINGS: PROFILE {profile_id}")
    print(f" Privacy Exposure Index: {exposure_summary['exposure_score']} / 100 ({exposure_summary['exposure_tier']})")
    print(f" Rounds Executed: {result['rounds_executed']} | Loop Iterations: {result['loop_iterations']}")
    print(f" Trace Written:   {result['trace_file']}")
    print(f" Report Markdown: {md_path}")
    print(f" Report JSON:     {json_path}")
    print("=" * 70)

    for i, (f, cf, rem) in enumerate(zip(findings, counterfactual_evals, remediation_plans), 1):
        verdict_str = f.verdict.value.upper()
        print(f"\n{i}. [{verdict_str}] {f.claim}")
        print(f"   Category:        {f.category}")
        print(f"   Confidence:      {f.confidence * 100:.0f}%")
        print(f"   Risk Level:      {f.risk_level.name} (Level {f.risk_level.value})")
        if f.attacker_models:
            print(f"   Attacker Models: {', '.join(m.value for m in f.attacker_models)}")
        if f.remediation:
            print(f"   Fix:             {f.remediation}")
        if cf.get("linchpin_facts"):
            print(f"   Linchpin Fact:   [{cf['linchpin_facts'][0]}] -> {cf['summary_explanation'][:90]}...")

        # Print evidence chain
        print("   Evidence Chain:")
        for step in f.evidence_chain:
            node_type = step.get("_type", "Entity")
            node_id = step.get("_id", "unknown")
            desc = step.get("value") or step.get("claim") or step.get("name") or step.get("pattern") or ""
            desc_clean = str(desc).encode("ascii", errors="replace").decode("ascii")
            src = step.get("_source", "")
            print(f"     -> [{node_type}] ({node_id[:8]}) {desc_clean} (source: {src})")

    print("\n" + "=" * 70)
    print(f" [dd] Privacy audit for Profile {profile_id} completed successfully.")
    print("=" * 70)


async def run_all_profiles(sample_mode: bool | None = None) -> None:
    """Run privacy audits across all three synthetic personas (A, B, C)."""
    for pid in ["A", "B", "C"]:
        await run_audit(pid, sample_mode=sample_mode)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Digital Doppelgänger privacy audit")
    parser.add_argument(
        "--profile",
        type=str,
        default="A",
        choices=["A", "B", "C", "ALL"],
        help="Profile to audit (A, B, C, or ALL)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Force sample mode (offline DuckDB and replay cache) regardless of .env",
    )
    args = parser.parse_args()
    sample_override = True if args.sample else None

    if args.profile == "ALL":
        asyncio.run(run_all_profiles(sample_mode=sample_override))
    else:
        asyncio.run(run_audit(args.profile, sample_mode=sample_override))


if __name__ == "__main__":
    main()
