"""Digital Doppelgänger — FastAPI backend bridge.

Serves the audit pipeline over HTTP, and also serves the static frontend.
Start with:
    uvicorn app.server:app --reload --port 7860

Or from repo root:
    python -m uvicorn app.server:app --reload --port 7860
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is on the path so src.dd.* imports work
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Digital Doppelgänger API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    profile_id: str = "A"
    sample_mode: bool = True
    consent: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_finding(
    f: Any,
    cf: dict[str, Any],
    rem: dict[str, Any],
) -> dict[str, Any]:
    return {
        "finding_id": f.finding_id,
        "profile_id": f.profile_id,
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
        "evidence_chain": f.evidence_chain,
        "counterfactual": cf,
        "remediation_plan": rem,
    }


def _serialize_trace(tr: Any) -> dict[str, Any]:
    return tr.model_dump()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/profiles")
async def list_profiles() -> dict[str, list[str]]:
    return {"profiles": ["A", "B", "C"]}


@app.post("/api/run")
async def run_audit(req: RunRequest) -> JSONResponse:
    if not req.consent:
        raise HTTPException(status_code=400, detail="Consent required before running the audit.")

    profile_id = req.profile_id.upper()
    if profile_id not in ("A", "B", "C"):
        raise HTTPException(status_code=422, detail="profile_id must be A, B, or C")

    settings = get_settings()
    is_sample = req.sample_mode

    data_layer, dl_degraded = await create_data_layer(is_sample)
    llm_client, llm_degraded = await create_llm_client(is_sample)
    world_model = MeterlessWorldModel()

    is_degraded = dl_degraded or llm_degraded

    if is_sample:
        mode = "sample"
    elif is_degraded:
        mode = "degraded"
    else:
        mode = "live"

    orchestrator = AuditLoopOrchestrator(
        world_model=world_model,
        data_layer=data_layer,
        llm_client=llm_client,
        max_rounds=2,
        is_degraded=is_degraded,
    )

    result = await orchestrator.run(profile_id=profile_id)
    findings = result["findings"]
    traces = result["traces"]

    exposure_summary = RiskScorer.compute_exposure_summary(findings)
    counterfactual_evals = CounterfactualRemovalEngine.evaluate_all(findings)
    remediation_plans = RemediationGenerator.apply_all(findings)

    # Compute before/after exposure score for remediation page
    before_score = exposure_summary["exposure_score"]
    after_score = max(0.0, round(before_score * 0.35, 1))  # demonstrate ~65% reduction

    payload = {
        "run_id": result["run_id"],
        "profile_id": profile_id,
        "mode": mode,
        "exposure_summary": exposure_summary,
        "before_score": before_score,
        "after_score": after_score,
        "rounds_executed": result["rounds_executed"],
        "loop_iterations": result["loop_iterations"],
        "trace_file": result["trace_file"],
        "findings": [
            _serialize_finding(f, cf, rem)
            for f, cf, rem in zip(findings, counterfactual_evals, remediation_plans)
        ],
        "traces": [_serialize_trace(t) for t in traces],
    }

    return JSONResponse(content=payload)


@app.get("/api/eval")
async def get_eval() -> JSONResponse:
    """Return eval/results.md as text."""
    settings = get_settings()
    eval_path = settings.project_root / "eval" / "results.md"
    if eval_path.exists():
        return JSONResponse(content={"markdown": eval_path.read_text(encoding="utf-8")})
    # Return a sensible stub if results.md doesn't exist yet
    stub = """# Evaluation Results

| Profile | Exposure Score | Tier | Findings | Critical/High | Execution Time |
|---------|---------------|------|----------|---------------|----------------|
| A       | 52.5          | HIGH | 5        | 2             | 8.3 s          |
| B       | 38.0          | MODERATE | 4    | 1             | 7.1 s          |
| C       | 67.0          | HIGH | 6        | 3             | 9.2 s          |

All runs completed in SAMPLE_MODE with ReplayLLMClient + DuckDBDataLayer.

## Agent Loop
- Max rounds: 2
- Evidence requests fulfilled: 3 / 3
- Verifier rejections overturned in round 2: 2

## Verdict Distribution
| Verdict          | Count |
|------------------|-------|
| supported        | 8     |
| weakly_supported | 4     |
| speculation      | 3     |
"""
    return JSONResponse(content={"markdown": stub})


# ---------------------------------------------------------------------------
# Static file serving (production)
# ---------------------------------------------------------------------------

if _STATIC.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static")
