"""Remediation Generator for Digital Doppelgänger.

Synthesizes prioritized, actionable privacy countermeasures corresponding to identified
linchpin facts and adversarial threat models.
"""

from __future__ import annotations

from typing import Any

from src.dd.models.domain import Finding, RiskLevel, VerdictLabel


class RemediationGenerator:
    """Generates concrete remediation actions and updates findings with specific fixes."""

    REMEDIATION_CATALOG: dict[str, dict[str, Any]] = {
        "location": {
            "title": "Enable Geofenced Privacy Zones on Fitness Applications",
            "category": "Platform Configuration",
            "steps": [
                "Open Strava / fitness tracking Settings > Privacy Controls > Map Visibility.",
                "Specify a custom privacy radius (at least 500m / 0.5 miles) around your residential address.",
                "Ensure default activity visibility is set to 'Followers' or 'Only You', not 'Everyone'.",
            ],
            "impact": "Hides starting and ending coordinates, breaking spatial clustering from food deliveries.",
        },
        "absence": {
            "title": "Enforce Delayed Social Travel Broadcast Policy",
            "category": "Operational Security",
            "steps": [
                "Adopt a strict post-vacation publishing policy: share photos and check-ins only AFTER returning home.",
                "Verify home security systems / timers before departure to avoid obvious signs of vacancy.",
                "Set personal calendar events containing travel itineraries to 'Private' mode.",
            ],
            "impact": "Eliminates real-time broadcast of vacant residential property to potential burglars.",
        },
        "routine": {
            "title": "Randomize Running Routes & Restrict Telemetry Publishing",
            "category": "Behavioral",
            "steps": [
                "Vary start times and running paths across alternating days of the week.",
                "Disable automated social media sharing / live beacon broadcasts for regular workouts.",
                "Audit workout privacy permissions so segment leaderboards do not broadcast your schedule.",
            ],
            "impact": "Prevents hostile stalkers from predicting your physical presence at fixed times.",
        },
        "health_exposure": {
            "title": "Restrict Health Calendar Metadata & Disassociate Medical Orders",
            "category": "Platform Configuration",
            "steps": [
                "Mark all medical and specialist consultations on calendar applications as 'Busy / Private' without venue details.",
                "Use pseudonymous or separate payment cards and shipping addresses for specialty pharmacy orders.",
                "Opt out of health service data broker sharing agreements under HIPAA / GDPR settings.",
            ],
            "impact": "Shields sensitive health conditions from insurance underwriters, employers, and data brokers.",
        },
        "financial_insurer": {
            "title": "Enforce Medical Privacy on Prescriptions & Underwriting Records",
            "category": "Operational Security",
            "steps": [
                "Request strict confidential communications for all prescription pickups and pharmacy notices.",
                "Review employee benefits dashboard to ensure voluntary health app sync is turned off.",
            ],
            "impact": "Prevents adverse insurance tiering and employment discrimination.",
        },
        "identity_kba": {
            "title": "Deprecate Knowledge-Based Authentication (KBA) & Scrub Bio Details",
            "category": "Identity Protection",
            "steps": [
                "Replace pet names, maiden names, and high schools in banking security questions with random passphrases.",
                "Remove birth dates, high school graduation years, and pet names from public social media profiles.",
                "Upgrade all banking and critical accounts to hardware-based FIDO2 / WebAuthn MFA.",
            ],
            "impact": "Immunizes accounts against social-engineering resets and credential stuffing attacks.",
        },
        "lifestyle": {
            "title": "Anonymize Delivery Accounts & Randomize Order Destinations",
            "category": "Consumer Privacy",
            "steps": [
                "Use an abbreviated name or initials on food delivery apps (e.g., 'V. B.' instead of full name).",
                "Select 'Meet outside' or neighborhood pickup spots when ordering during off-peak hours.",
            ],
            "impact": "Mitigates lifestyle and habit profiling by commercial data aggregators.",
        },
        "employment": {
            "title": "Clarify Employment Hours & Maintain Professional Compartmentalization",
            "category": "Advisory",
            "steps": [
                "Keep employer accounts and personal device credentials segregated.",
                "No action required for disproven decoys.",
            ],
            "impact": "Neutralizes inaccurate employment assumptions.",
        },
    }

    @classmethod
    def generate_remediation(cls, finding: Finding) -> dict[str, Any]:
        """Generate structured remediation metadata and update the finding's fix."""
        if finding.verdict == VerdictLabel.SPECULATION:
            finding.remediation = (
                "No remediation required: Claim evaluated as uncorroborated speculation by the verifier."
            )
            return {
                "title": "No Action Required",
                "priority": "Advisory",
                "category": "Advisory",
                "steps": ["No security modification needed."],
                "impact": "Neutralizes unverified claim.",
            }

        catalog_entry = cls.REMEDIATION_CATALOG.get(
            finding.category,
            {
                "title": f"Review and Restrict Public Data Exposure ({finding.category.title()})",
                "category": "Operational",
                "steps": [
                    "Audit account privacy settings for this category.",
                    "Remove redundant public disclosures.",
                ],
                "impact": "Reduces adversarial correlation capacity.",
            },
        )

        # Determine priority from risk level
        if finding.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            priority = "Immediate (Within 24 Hours)"
        elif finding.risk_level == RiskLevel.MODERATE:
            priority = "Short-Term (Within 7 Days)"
        else:
            priority = "Best Practice"

        # Update finding's text remediation
        summary_fix = f"{catalog_entry['title']}: {catalog_entry['steps'][0]}"
        finding.remediation = summary_fix

        return {
            "title": catalog_entry["title"],
            "priority": priority,
            "category": catalog_entry["category"],
            "steps": catalog_entry["steps"],
            "impact": catalog_entry["impact"],
        }

    @classmethod
    def apply_all(cls, findings: list[Finding]) -> list[dict[str, Any]]:
        """Apply remediations to all findings and return structured action list."""
        return [cls.generate_remediation(f) for f in findings]
