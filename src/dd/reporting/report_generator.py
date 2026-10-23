"""Comprehensive Report Generator for Digital Doppelgänger.

Generates dual audit artifacts:
1. Rich, visual Markdown reports with Mermaid graph diagrams and counterfactual proofs.
2. Machine-readable JSON reports conforming to standardized privacy audit schemas.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.dd.models.domain import Finding, VerdictLabel


class ReportGenerator:
    """Generates and exports Markdown and JSON audit reports."""

    @classmethod
    def generate_markdown(
        cls,
        profile_id: str,
        findings: list[Finding],
        exposure_summary: dict[str, Any],
        counterfactual_evals: list[dict[str, Any]],
        remediation_plans: list[dict[str, Any]],
        trace_file: str = "",
    ) -> str:
        """Render a formatted, rich Markdown privacy audit report with Mermaid diagrams."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        score = exposure_summary.get("exposure_score", 0.0)
        tier = exposure_summary.get("exposure_tier", "UNKNOWN")
        level_counts = exposure_summary.get("level_counts", {})

        md: list[str] = []
        md.append(f"# Digital Doppelgänger: Multi-Agent Privacy Audit Report")
        md.append(f"**Target Persona:** Profile {profile_id} | **Audit Generated:** {timestamp}")
        md.append(f"**Audit Trace:** `{trace_file}`\n")
        md.append("---\n")

        # 1. Executive Summary & Exposure Meter
        md.append("## 1. Executive Summary & Exposure Index\n")
        md.append(f"> **PRIVACY EXPOSURE INDEX: {score} / 100 ({tier})**")
        md.append(f"> *{exposure_summary.get('summary_description', '')}*\n")

        md.append("| Metric | Value | Description |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Overall Exposure** | **{score} / 100** | Weighted privacy vulnerability index |")
        md.append(f"| **Risk Tier** | **{tier}** | Action urgency tier |")
        md.append(f"| **Top Risk Driver** | {exposure_summary.get('top_risk_driver')} | Primary corroborated leak |")
        md.append(f"| **Critical / High Risks** | {level_counts.get('CRITICAL', 0) + level_counts.get('HIGH', 0)} | Severe physical or credential exposures |")
        md.append(f"| **Moderate Risks** | {level_counts.get('MODERATE', 0)} | Behavioral and routine profiling |")
        md.append(f"| **Informational / Decoys** | {level_counts.get('INFORMATIONAL', 0)} | Refuted or uncorroborated hypotheses |\n")

        # 2. Key Findings & Corroborated Evidence Chains
        md.append("## 2. Adversarial Privacy Inferences & Evidence Chains\n")

        for idx, (f, cf, rem) in enumerate(zip(findings, counterfactual_evals, remediation_plans), 1):
            verdict_badge = f.verdict.value.upper()
            risk_badge = f"{f.risk_level.name} (Level {f.risk_level.value})"
            attackers = ", ".join(m.value for m in f.attacker_models) if f.attacker_models else "None"

            md.append(f"### Finding {idx}: {f.claim}\n")
            md.append(f"- **Verdict:** `{verdict_badge}`")
            md.append(f"- **Risk Level:** `{risk_badge}`")
            md.append(f"- **Confidence:** `{int(f.confidence * 100)}%`")
            md.append(f"- **Threat Models:** `{attackers}`")
            md.append(f"- **Category:** `{f.category}`\n")

            # Evidence Chain Table
            md.append("#### Corroborated Evidence Chain")
            md.append("| Node Type | Entity ID | Source Data / Extraction | Extracted Observation |")
            md.append("| :--- | :--- | :--- | :--- |")
            for node in f.evidence_chain:
                ntype = node.get("_type", "Entity")
                nid = node.get("_id", "unknown")[:8]
                src = node.get("_source", "")
                val = str(node.get("value") or node.get("claim") or node.get("pattern") or node.get("name") or "")[:70]
                # Clean ASCII
                val_clean = val.replace("|", "/")
                md.append(f"| `{ntype}` | `{nid}` | `{src}` | {val_clean} |")
            md.append("")

            # Mermaid Diagram
            if len(f.evidence_chain) >= 2:
                md.append("```mermaid")
                md.append("graph TD")
                # Build simple directed graph from chain
                chain_nodes = f.evidence_chain
                for c_i in range(len(chain_nodes) - 1):
                    src_n = chain_nodes[c_i]
                    dst_n = chain_nodes[c_i + 1]
                    s_id = src_n.get("_id", f"n{c_i}")[:6]
                    d_id = dst_n.get("_id", f"n{c_i+1}")[:6]
                    s_lbl = f"{src_n.get('_type')}: {str(src_n.get('value', src_n.get('_id', '')))[:20]}".replace('"', "'")
                    d_lbl = f"{dst_n.get('_type')}: {str(dst_n.get('value', dst_n.get('_id', '')))[:20]}".replace('"', "'")
                    md.append(f'    {s_id}["{s_lbl}"] --> {d_id}["{d_lbl}"]')
                md.append("```\n")

            # Counterfactual Proof Section
            md.append("#### Causal Explanation & Counterfactual Proof")
            md.append(f"> **Why This Matters:** {cf.get('summary_explanation', '')}\n")
            if cf.get("excision_results"):
                md.append("| Linchpin Fact | Source Table | Pre-Removal Conf | Post-Removal Conf | Excision Impact |")
                md.append("| :--- | :--- | :--- | :--- | :--- |")
                for ex in cf["excision_results"]:
                    md.append(
                        f"| `{ex['fact_id'][:8]}` | `{ex['source']}` | "
                        f"{int(ex['pre_removal_confidence'] * 100)}% | **{int(ex['post_removal_confidence'] * 100)}%** | "
                        f"{ex['impact_explanation']} |"
                    )
                md.append("")

            # Prescribed Remediation
            md.append("#### Actionable Remediation")
            md.append(f"- **Action:** **{rem.get('title')}** (`{rem.get('priority')}`)")
            md.append(f"- **Impact:** {rem.get('impact')}")
            md.append("  - Concrete steps:")
            for s in rem.get("steps", []):
                md.append(f"    - {s}")
            md.append("\n---\n")

        # 3. Consolidated Remediation Checklist
        md.append("## 3. Prioritized Remediation Checklist\n")
        md.append("Execute these steps to neutralize the identified cross-source privacy leaks:\n")

        for rem in remediation_plans:
            if rem.get("title") != "No Action Required":
                md.append(f"### [ ] {rem.get('title')} ({rem.get('priority')})")
                md.append(f"- **Domain:** {rem.get('category')} | **Expected Benefit:** {rem.get('impact')}")
                for s in rem.get("steps", []):
                    md.append(f"  - [ ] {s}")
                md.append("")

        return "\n".join(md)

    @classmethod
    def generate_json(
        cls,
        profile_id: str,
        findings: list[Finding],
        exposure_summary: dict[str, Any],
        counterfactual_evals: list[dict[str, Any]],
        remediation_plans: list[dict[str, Any]],
        trace_file: str = "",
    ) -> dict[str, Any]:
        """Generate structured, machine-readable JSON privacy audit artifact."""
        return {
            "audit_schema_version": "1.0.0",
            "audit_metadata": {
                "profile_id": profile_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "trace_file": trace_file,
                "engine": "Digital Doppelgänger Multi-Agent Auditor",
            },
            "exposure_summary": exposure_summary,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "claim": f.claim,
                    "category": f.category,
                    "verdict": f.verdict.value,
                    "confidence": f.confidence,
                    "risk_level": {
                        "value": f.risk_level.value,
                        "name": f.risk_level.name,
                    },
                    "attacker_models": [m.value for m in f.attacker_models],
                    "remediation": f.remediation,
                    "counterfactual": cf,
                    "remediation_plan": rem,
                    "evidence_chain": f.evidence_chain,
                }
                for f, cf, rem in zip(findings, counterfactual_evals, remediation_plans)
            ],
            "action_checklist": [
                rem for rem in remediation_plans if rem.get("title") != "No Action Required"
            ],
        }

    @classmethod
    def save_reports(
        cls,
        reports_dir: Path,
        profile_id: str,
        findings: list[Finding],
        exposure_summary: dict[str, Any],
        counterfactual_evals: list[dict[str, Any]],
        remediation_plans: list[dict[str, Any]],
        trace_file: str = "",
    ) -> tuple[Path, Path]:
        """Save both Markdown and JSON reports to disk."""
        reports_dir.mkdir(parents=True, exist_ok=True)

        md_content = cls.generate_markdown(
            profile_id=profile_id,
            findings=findings,
            exposure_summary=exposure_summary,
            counterfactual_evals=counterfactual_evals,
            remediation_plans=remediation_plans,
            trace_file=trace_file,
        )
        json_content = cls.generate_json(
            profile_id=profile_id,
            findings=findings,
            exposure_summary=exposure_summary,
            counterfactual_evals=counterfactual_evals,
            remediation_plans=remediation_plans,
            trace_file=trace_file,
        )

        md_path = reports_dir / f"privacy_audit_profile_{profile_id}.md"
        json_path = reports_dir / f"privacy_audit_profile_{profile_id}.json"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_content, f, indent=2)

        return md_path, json_path
