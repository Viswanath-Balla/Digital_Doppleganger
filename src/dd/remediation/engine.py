"""Deterministic counterfactual remediation engine.

Simulates fact and source excision against essential fact dependencies to find
the actions that collapse the most inference chains per unit of user effort.
Makes zero LLM calls.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.dd.analysis.risk_scorer import RiskScorer
from src.dd.models.domain import Finding, RiskLevel, VerdictLabel
from src.dd.remediation.cost_model import ActionType, RemediationCostModel


class RemediationAction(BaseModel):
    """A ranked counterfactual remediation action."""

    action_id: str = Field(default_factory=lambda: f"act_{uuid4().hex[:8]}")
    action_type: ActionType
    target_id: str
    target_label: str
    source_table: str
    cost: int
    collapsed_inference_ids: list[str] = Field(default_factory=list)
    collapsed_claims: list[str] = Field(default_factory=list)
    exposure_before: float
    exposure_after: float
    exposure_reduction: float
    efficiency: float
    what_to_do: str
    why_it_helps: str
    what_it_will_not_fix: str


class RemediationSimulationResult(BaseModel):
    """End-to-end result of counterfactual remediation simulation."""

    profile_id: str
    exposure_before: float
    exposure_after: float
    exposure_reduction: float
    top_linchpin_fact_id: str | None = None
    top_linchpin_collapsed_chains: int = 0
    ranked_actions: list[RemediationAction] = Field(default_factory=list)


class RemediationEngine:
    """Deterministic counterfactual simulation engine."""

    @staticmethod
    def evaluate_collapse(
        finding: Finding,
        removed_fact_ids: set[str],
        removed_sources: set[str] | None = None,
    ) -> bool:
        """Check if an inference collapses upon removing specified facts or sources."""
        if finding.verdict == VerdictLabel.SPECULATION:
            return False

        # 1. Removal of any essential fact collapses the inference
        essential = set(finding.essential_fact_ids)
        if essential and bool(essential.intersection(removed_fact_ids)):
            return True

        # Fallback to linchpins if essential_fact_ids empty
        if not essential and finding.linchpin_facts:
            if bool(set(finding.linchpin_facts).intersection(removed_fact_ids)):
                return True

        # 2. Independent source minimum check
        active_sources = set()
        for node in finding.evidence_chain:
            node_id = node.get("_id") or node.get("id")
            src_table = node.get("source_table")
            if not src_table:
                continue
            if removed_sources and src_table in removed_sources:
                continue
            if node_id and node_id in removed_fact_ids:
                continue
            active_sources.add(src_table)

        if len(active_sources) < finding.min_independent_sources:
            return True

        return False

    @classmethod
    def run_simulation(
        cls, profile_id: str, findings: list[Finding]
    ) -> RemediationSimulationResult:
        """Run counterfactual simulations across all candidate actions and rank by ROI."""
        # 1. Baseline exposure score
        baseline_summary = RiskScorer.compute_exposure_summary(findings)
        exposure_before = baseline_summary["exposure_score"]

        verified_findings = [
            f for f in findings if f.verdict in (VerdictLabel.SUPPORTED, VerdictLabel.WEAKLY_SUPPORTED)
        ]

        if not verified_findings:
            return RemediationSimulationResult(
                profile_id=profile_id,
                exposure_before=exposure_before,
                exposure_after=exposure_before,
                exposure_reduction=0.0,
                ranked_actions=[],
            )

        candidate_actions: list[RemediationAction] = []
        fact_collapse_counts: dict[str, int] = {}

        # 2. Collect unique candidate targets from evidence chains & essential facts
        seen_targets: set[str] = set()

        for f in verified_findings:
            chain_facts = [
                n for n in f.evidence_chain if n.get("_type") in ("Fact", "fact") or "source_table" in n
            ]

            for fact in chain_facts:
                fact_id = fact.get("_id") or fact.get("id")
                if not fact_id or fact_id in seen_targets:
                    continue
                seen_targets.add(fact_id)

                src_table = fact.get("source_table", "")
                val_str = str(fact.get("value", fact.get("claim", "")))

                # Determine action type and cost
                if "social" in src_table:
                    act_type = ActionType.DELETE_POST
                    cost = RemediationCostModel.get_cost(act_type)
                    what_to_do = f"Delete or archive the social post referencing '{val_str[:50]}...'"
                    why_it_helps = "Removes public timeline confirmation and breaks cross-source temporal correlation."
                    what_it_will_not_fix = "Does not retroactively purge cached mirrors or existing web scraper snapshots."
                elif "strava" in src_table or "food" in src_table or "lat" in fact or "coord" in fact:
                    act_type = ActionType.GENERALIZE_FIELD
                    cost = RemediationCostModel.get_cost(act_type)
                    what_to_do = f"Generalize location precision for {src_table} (e.g. city-level obfuscation or privacy zone)."
                    why_it_helps = f"Disrupts GPS distance clustering around home coordinate radius without disabling the service."
                    what_it_will_not_fix = "General geographic regional presence remains discoverable."
                elif "profile" in src_table or "account" in src_table or "pet" in val_str.lower() or "1996" in val_str:
                    act_type = ActionType.CHANGE_RECOVERY_ANSWER
                    cost = RemediationCostModel.get_cost(act_type)
                    what_to_do = f"Rotate security question answers and privacy settings on linked accounts."
                    why_it_helps = "Breaks knowledge-based authentication attack paths that reuse personal attributes."
                    what_it_will_not_fix = "Historical data leaks from other third-party breaches remain unaffected."
                else:
                    act_type = ActionType.GENERALIZE_FIELD
                    cost = RemediationCostModel.get_cost(act_type)
                    what_to_do = f"Remove or restrict visibility of {src_table} record ({fact_id})."
                    why_it_helps = "Collapses downstream entity derivation and multi-hop inference entailment."
                    what_it_will_not_fix = "Independent corroboration through public records may still exist."

                # Simulate excision
                collapsed_ids = []
                collapsed_claims = []
                remaining_findings = []

                for other_f in findings:
                    if cls.evaluate_collapse(other_f, removed_fact_ids={fact_id}):
                        collapsed_ids.append(other_f.finding_id)
                        collapsed_claims.append(other_f.claim)
                    else:
                        remaining_findings.append(other_f)

                fact_collapse_counts[fact_id] = len(collapsed_ids)

                if collapsed_ids:
                    after_summary = RiskScorer.compute_exposure_summary(remaining_findings)
                    exp_after = after_summary["exposure_score"]
                    reduction = max(0.0, exposure_before - exp_after)
                    efficiency = round(reduction / max(1, cost), 2)

                    candidate_actions.append(
                        RemediationAction(
                            action_type=act_type,
                            target_id=fact_id,
                            target_label=val_str[:70],
                            source_table=src_table,
                            cost=cost,
                            collapsed_inference_ids=collapsed_ids,
                            collapsed_claims=collapsed_claims,
                            exposure_before=round(exposure_before, 1),
                            exposure_after=round(exp_after, 1),
                            exposure_reduction=round(reduction, 1),
                            efficiency=efficiency,
                            what_to_do=what_to_do,
                            why_it_helps=why_it_helps,
                            what_it_will_not_fix=what_it_will_not_fix,
                        )
                    )

        # 3. Candidate Source-Level Excisions
        source_tables = {n.get("source_table") for f in verified_findings for n in f.evidence_chain if n.get("source_table")}
        for src in source_tables:
            if not src:
                continue
            cost = RemediationCostModel.get_cost(ActionType.REMOVE_DATA_SOURCE)
            collapsed_ids = []
            collapsed_claims = []
            remaining_findings = []

            for f in findings:
                if cls.evaluate_collapse(f, removed_fact_ids=set(), removed_sources={src}):
                    collapsed_ids.append(f.finding_id)
                    collapsed_claims.append(f.claim)
                else:
                    remaining_findings.append(f)

            if collapsed_ids:
                after_summary = RiskScorer.compute_exposure_summary(remaining_findings)
                exp_after = after_summary["exposure_score"]
                reduction = max(0.0, exposure_before - exp_after)
                efficiency = round(reduction / cost, 2)

                candidate_actions.append(
                    RemediationAction(
                        action_type=ActionType.REMOVE_DATA_SOURCE,
                        target_id=src,
                        target_label=f"Complete removal/disconnection of data export for '{src}'",
                        source_table=src,
                        cost=cost,
                        collapsed_inference_ids=collapsed_ids,
                        collapsed_claims=collapsed_claims,
                        exposure_before=round(exposure_before, 1),
                        exposure_after=round(exp_after, 1),
                        exposure_reduction=round(reduction, 1),
                        efficiency=efficiency,
                        what_to_do=f"Disconnect or revoke access to the '{src}' platform export.",
                        why_it_helps=f"Completely removes all factual telemetry contributed by {src}.",
                        what_it_will_not_fix=f"Disables legitimate app utilities provided by {src}.",
                    )
                )

        # 4. Rank actions by efficiency (ROI) descending, then exposure reduction
        candidate_actions.sort(
            key=lambda a: (a.efficiency, a.exposure_reduction, -a.cost), reverse=True
        )

        # 5. Top linchpin fact
        top_fact_id = None
        top_fact_count = 0
        if fact_collapse_counts:
            sorted_facts = sorted(fact_collapse_counts.items(), key=lambda kv: kv[1], reverse=True)
            if sorted_facts and sorted_facts[0][1] > 0:
                top_fact_id, top_fact_count = sorted_facts[0]

        # 6. Overall post-remediation score if top actions applied
        post_score = candidate_actions[0].exposure_after if candidate_actions else exposure_before
        overall_reduction = round(exposure_before - post_score, 1)

        return RemediationSimulationResult(
            profile_id=profile_id,
            exposure_before=round(exposure_before, 1),
            exposure_after=round(post_score, 1),
            exposure_reduction=overall_reduction,
            top_linchpin_fact_id=top_fact_id,
            top_linchpin_collapsed_chains=top_fact_count,
            ranked_actions=candidate_actions,
        )
