"""Agent communication and execution trace schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from src.dd.models.domain import EvidenceRequest, Finding, Inference, Verdict


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentMessage(BaseModel):
    """Standard message envelope exchanged between agents in the loop."""

    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex[:8]}")
    sender: str
    recipient: str
    message_type: Literal[
        "plan",
        "evidence_request",
        "extracted_facts",
        "candidate_inference",
        "verdict",
        "revision_request",
        "final_report"
    ]
    payload: dict[str, Any] = Field(default_factory=dict)
    round_num: int = 1
    timestamp: str = Field(default_factory=_utc_now_str)


class TraceRecord(BaseModel):
    """Single line trace record written to runs/<run_id>/trace.jsonl."""

    run_id: str
    step: int
    agent: str
    message_type: str
    model: str
    provider: str = "nightshift"
    degraded: bool = False
    latency_ms: float = 0.0
    retry_count: int = 0
    outcome: Literal["success", "failure", "downgrade", "rejected", "evidence_requested"] = "success"
    prompt_file: str | None = None
    prompt_version: str | None = None
    prompt_sha256: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_utc_now_str)
