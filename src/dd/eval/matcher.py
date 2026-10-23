"""Ground-truth leak matcher and causal faithfulness validator."""

from __future__ import annotations

import json
from typing import Any

from src.dd.models.domain import Finding, VerdictLabel


class LeakMatcher:
    """Matches agent findings with synthetic ground truth items and checks causal grounding."""

    # Keywords mapping ground truth inference IDs to claim tokens (specific to general)
    MATCH_RULES: dict[str, list[str]] = {
        "A_INF_HOME_ADDR": ["home address", "742 evergreen"],
        "A_INF_MORNING_ROUTINE": ["morning running routine", "weekday morning", "06:30"],
        "A_INF_ABSENCE_WINDOW": ["vacation in hawaii", "vacant", "july 10-20"],
        "A_INF_DECOY_NIGHTSHIFT": ["night shift"],
        "B_INF_INSURER_EXPOSURE": ["underwriting", "immunology", "supportive treatments"],
        "B_INF_SPECIALIST_VISITS": ["specialist consultations", "oakridge oncology"],
        "B_INF_DECOY_CONDITION": ["lymphoma"],
        "C_INF_DOB": ["may 14, 1996", "birth is may 14", "1996"],
        "C_INF_PET_NAME": ["barnaby", "golden retriever"],
        "C_INF_FIRST_SCHOOL": ["oakfield elementary", "first school"],
        "C_INF_DECOY_MAIDEN_NAME": ["vance", "maiden name"],
    }

    @classmethod
    def match_finding_to_ground_truth(
        cls, finding: Finding, gt_items: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find matching ground truth item for a given finding."""
        claim_lower = finding.claim.lower()

        # Check each ground truth rule
        for item in gt_items:
            inf_id = item.get("inference_id", "")
            keywords = cls.MATCH_RULES.get(inf_id, [])

            if any(kw in claim_lower for kw in keywords):
                return item

        return None

    @classmethod
    def evaluate_causal_faithfulness(
        cls, finding: Finding, gt_item: dict[str, Any]
    ) -> tuple[int, int, float]:
        """Check how many required ground truth fact refs are present in the evidence chain.

        Returns:
            (matched_refs, total_required_refs, faithfulness_ratio)
        """
        required_refs = gt_item.get("required_fact_refs", [])
        if not required_refs:
            return 0, 0, 1.0

        matched_count = 0
        for ref in required_refs:
            req_table = ref.get("table", "").lower()
            req_val = str(ref.get("value", "")).lower()
            req_col = str(ref.get("key_col", "")).lower()

            ref_found = False
            for node in finding.evidence_chain:
                node_src = str(node.get("_source", "")).lower()
                node_tbl = str(node.get("source_table", "")).lower()
                node_str = json.dumps(node).lower()

                # Check if table matches
                table_matched = req_table in node_src or req_table == node_tbl or req_table in node_str

                # Check if value matches
                val_matched = (
                    req_val in node_str
                    or (len(req_val) >= 4 and req_val[:4] in node_str)
                    or (req_col and req_col in node and req_val in str(node[req_col]).lower())
                )

                if table_matched and val_matched:
                    ref_found = True
                    break
                elif table_matched and not req_val:
                    ref_found = True
                    break

            if ref_found:
                matched_count += 1

        ratio = matched_count / len(required_refs)
        return matched_count, len(required_refs), ratio
