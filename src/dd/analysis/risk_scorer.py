"""Risk Scoring Engine for Digital Doppelgänger.

Implements deterministic 5-level risk taxonomy (L1-L5), composite exposure index (0-100),
and threat actor attribution according to hackathon specifications.
"""

from __future__ import annotations

from typing import Any

from src.dd.models.domain import AttackerModel, Finding, RiskLevel, VerdictLabel


class RiskScorer:
    """Evaluates privacy findings and computes calibrated risk scores and threat models."""

    # Severity weights for composite score calculation
    SEVERITY_WEIGHTS = {
        RiskLevel.CRITICAL: 35.0,
        RiskLevel.HIGH: 25.0,
        RiskLevel.MODERATE: 15.0,
        RiskLevel.LOW: 5.0,
        RiskLevel.INFORMATIONAL: 0.0,
    }

    # Taxonomy mapping by category and sensitivity
    CATEGORY_BASE_SEVERITY: dict[str, RiskLevel] = {
        "location": RiskLevel.HIGH,
        "absence": RiskLevel.HIGH,
        "health_exposure": RiskLevel.HIGH,
        "identity_kba": RiskLevel.HIGH,
        "routine": RiskLevel.MODERATE,
        "financial_insurer": RiskLevel.MODERATE,
        "lifestyle": RiskLevel.LOW,
        "employment": RiskLevel.LOW,
        "health_diagnosis": RiskLevel.INFORMATIONAL,
    }

    # Attacker models mapped by privacy category
    CATEGORY_ATTACKERS: dict[str, list[AttackerModel]] = {
        "location": [AttackerModel.STALKER, AttackerModel.BURGLAR],
        "absence": [AttackerModel.BURGLAR],
        "routine": [AttackerModel.STALKER],
        "health_exposure": [AttackerModel.INSURER, AttackerModel.EMPLOYER, AttackerModel.SCAMMER],
        "financial_insurer": [AttackerModel.INSURER],
        "identity_kba": [AttackerModel.SCAMMER, AttackerModel.DATA_BROKER],
        "employment": [AttackerModel.EMPLOYER, AttackerModel.BURGLAR],
        "lifestyle": [AttackerModel.SCAMMER],
        "health_diagnosis": [AttackerModel.INSURER],
    }

    @classmethod
    def score_finding(cls, finding: Finding) -> Finding:
        """Assign calibrated RiskLevel and AttackerModels to a finding."""
        # 1. Speculation / rejected hypotheses are always Informational
        if finding.verdict == VerdictLabel.SPECULATION:
            finding.risk_level = RiskLevel.INFORMATIONAL
            if not finding.attacker_models:
                finding.attacker_models = cls.CATEGORY_ATTACKERS.get(
                    finding.category, [AttackerModel.SCAMMER]
                )
            return finding

        # 2. Base severity from category
        base_sev = cls.CATEGORY_BASE_SEVERITY.get(finding.category, RiskLevel.MODERATE)

        # 3. Calibrate based on confidence and verdict
        if finding.verdict == VerdictLabel.SUPPORTED:
            if finding.confidence >= 0.95 and base_sev == RiskLevel.HIGH:
                # Direct home address or explicit absence can escalate to Critical if confidence is extreme
                if finding.category in ("location", "absence"):
                    finding.risk_level = RiskLevel.HIGH  # High impact physical risk
                else:
                    finding.risk_level = base_sev
            else:
                finding.risk_level = base_sev
        elif finding.verdict == VerdictLabel.WEAKLY_SUPPORTED:
            # Downgrade one tier for weak corroboration
            if base_sev == RiskLevel.HIGH:
                finding.risk_level = RiskLevel.MODERATE
            elif base_sev == RiskLevel.MODERATE:
                finding.risk_level = RiskLevel.LOW
            else:
                finding.risk_level = RiskLevel.INFORMATIONAL
        else:
            finding.risk_level = RiskLevel.INFORMATIONAL

        # 4. Assign attacker models if not already set
        if not finding.attacker_models:
            finding.attacker_models = cls.CATEGORY_ATTACKERS.get(
                finding.category, [AttackerModel.SCAMMER]
            )

        return finding

    @classmethod
    def compute_exposure_summary(cls, findings: list[Finding]) -> dict[str, Any]:
        """Compute composite Privacy Exposure Index (0-100) and risk breakdown."""
        scored_findings = [cls.score_finding(f) for f in findings]

        raw_score = 0.0
        level_counts: dict[str, int] = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MODERATE": 0,
            "LOW": 0,
            "INFORMATIONAL": 0,
        }

        top_driver: Finding | None = None
        max_driver_impact = -1.0

        for f in scored_findings:
            level_name = f.risk_level.name
            level_counts[level_name] = level_counts.get(level_name, 0) + 1

            if f.verdict in (VerdictLabel.SUPPORTED, VerdictLabel.WEAKLY_SUPPORTED):
                w = cls.SEVERITY_WEIGHTS.get(f.risk_level, 0.0)
                impact = w * f.confidence
                raw_score += impact

                if impact > max_driver_impact:
                    max_driver_impact = impact
                    top_driver = f

        composite_score = min(100.0, round(raw_score, 1))

        if composite_score >= 80.0:
            tier = "CRITICAL"
            summary_desc = "Severe privacy exposure with multiple corroborated high-impact physical or identity vectors."
        elif composite_score >= 60.0:
            tier = "HIGH"
            summary_desc = "High privacy exposure enabling precise location, routine, or credential compromise."
        elif composite_score >= 35.0:
            tier = "MODERATE"
            summary_desc = "Moderate exposure allowing behavioral profiling and targeted spear-phishing."
        elif composite_score > 0.0:
            tier = "LOW"
            summary_desc = "Low exposure with limited or weak correlations."
        else:
            tier = "MINIMAL"
            summary_desc = "No verified privacy vulnerabilities identified."

        return {
            "exposure_score": composite_score,
            "exposure_tier": tier,
            "summary_description": summary_desc,
            "level_counts": level_counts,
            "total_findings": len(findings),
            "top_risk_driver": top_driver.claim if top_driver else "None",
            "top_driver_risk": top_driver.risk_level.name if top_driver else "INFORMATIONAL",
        }
