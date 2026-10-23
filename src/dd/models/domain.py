"""Domain models for Digital Doppelgänger.

Entities representing facts, hypotheses, verifier evaluations, and audit findings.
Designed for serialization, Pydantic v2 validation, and World Model graph ingestion.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class EntityType(str, Enum):
    PERSON = "Person"
    PLACE = "Place"
    TIME_PATTERN = "TimePattern"
    ACCOUNT = "Account"
    FACT = "Fact"
    INFERENCE = "Inference"
    EVIDENCE = "Evidence"


class RelationType(str, Enum):
    SUPPORTS = "SUPPORTS"
    DERIVED_FROM = "DERIVED_FROM"
    SAME_AS = "SAME_AS"
    CONTRADICTS = "CONTRADICTS"


class VerdictLabel(str, Enum):
    SUPPORTED = "supported"
    WEAKLY_SUPPORTED = "weakly_supported"
    SPECULATION = "speculation"


class RiskLevel(int, Enum):
    INFORMATIONAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5


class AttackerModel(str, Enum):
    STALKER = "stalker"
    SCAMMER = "scammer"
    BURGLAR = "burglar"
    EMPLOYER = "employer"
    INSURER = "insurer"
    DATA_BROKER = "data_broker"


# -----------------------------------------------------------------------------
# Core Domain Entities
# -----------------------------------------------------------------------------

class Fact(BaseModel):
    """An atomic factual observation extracted from raw data sources."""

    id: str | None = None
    profile_id: str
    source_table: str
    source_row_id: str | None = None
    entity_type: EntityType = EntityType.FACT
    key: str
    value: Any
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    observed_at: str | None = None
    extracted_by: str = "extractor"
    created_at: str = Field(default_factory=_utc_now_str)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Inference(BaseModel):
    """A hypothesis proposed by the Red-team agent correlating multiple facts."""

    id: str | None = None
    profile_id: str
    claim: str
    category: str
    attacker_models: list[AttackerModel] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    supporting_fact_ids: list[str] = Field(default_factory=list)
    status: Literal["proposed", "under_review", "verified", "rejected"] = "proposed"
    round_num: int = 1
    proposed_by: str = "red_team"
    created_at: str = Field(default_factory=_utc_now_str)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceRequest(BaseModel):
    """A request from the Verifier back to the Planner for missing evidence."""

    id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:8]}")
    inference_id: str
    requested_by: str = "verifier"
    target_table_or_entity: str
    predicate: str
    rationale: str
    created_at: str = Field(default_factory=_utc_now_str)


class Verdict(BaseModel):
    """Evaluation produced by the Verifier agent for a specific inference."""

    id: str = Field(default_factory=lambda: f"ver_{uuid4().hex[:8]}")
    inference_id: str
    label: VerdictLabel
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    rationale: str
    falsification_condition: str = ""
    strengthening_condition: str = ""
    verified_by: str = "verifier"
    model_name: str = "sample-stub"
    created_at: str = Field(default_factory=_utc_now_str)


class Finding(BaseModel):
    """Synthesized privacy risk finding ready for the audit report."""

    finding_id: str = Field(default_factory=lambda: f"fnd_{uuid4().hex[:8]}")
    profile_id: str
    category: str
    claim: str
    verdict: VerdictLabel
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.INFORMATIONAL
    attacker_models: list[AttackerModel] = Field(default_factory=list)
    evidence_chain: list[dict[str, Any]] = Field(default_factory=list)
    remediation: str = ""
    created_at: str = Field(default_factory=_utc_now_str)
