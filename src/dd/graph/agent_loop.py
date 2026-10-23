"""Non-linear multi-agent orchestration loop with bounded revision and evidence loops."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.dd.adapters.base import DataLayer, LLMClient, WorldModel
from src.dd.agents.extractor import ExtractorAgent
from src.dd.agents.linker import LinkerAgent
from src.dd.agents.planner import PlannerAgent
from src.dd.agents.red_team import RedTeamAgent
from src.dd.agents.verifier import VerifierAgent
from src.dd.analysis import (
    CounterfactualRemovalEngine,
    RemediationGenerator,
    RiskScorer,
)
from src.dd.config import get_settings
from src.dd.models.domain import (
    AttackerModel,
    EntityType,
    Finding,
    RelationType,
    RiskLevel,
    Verdict,
    VerdictLabel,
)
from src.dd.models.messages import TraceRecord


class AuditLoopOrchestrator:
    """Orchestrates Planner, Extractor, Linker, Red-Team, and Verifier across iterative feedback loops."""

    def __init__(
        self,
        world_model: WorldModel,
        data_layer: DataLayer,
        llm_client: LLMClient,
        max_rounds: int = 2,
        step_timeout_sec: float = 30.0,
        is_degraded: bool = False,
    ) -> None:
        self.world_model = world_model
        self.data_layer = data_layer
        self.llm_client = llm_client
        self.max_rounds = max_rounds
        self.step_timeout_sec = step_timeout_sec
        self.is_degraded = is_degraded

        # Instantiate agents
        self.planner = PlannerAgent(world_model, data_layer, llm_client)
        self.extractor = ExtractorAgent(world_model, data_layer, llm_client)
        self.linker = LinkerAgent(world_model, data_layer, llm_client)
        self.red_team = RedTeamAgent(world_model, data_layer, llm_client)
        self.verifier = VerifierAgent(world_model, data_layer, llm_client)

        self._step_counter = 0

    async def run(self, profile_id: str) -> dict[str, Any]:
        """Execute end-to-end privacy audit loop for the given profile."""
        settings = get_settings()
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        run_dir = settings.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        trace_file = run_dir / "trace.jsonl"

        traces: list[TraceRecord] = []
        all_verdicts: list[Verdict] = []
        findings: list[Finding] = []

        data_provider = "zetaris" if hasattr(self.data_layer, "database") else "duckdb"
        llm_provider = "nightshift" if not settings.sample_mode else "sample-stub"

        def log_trace(
            agent: str,
            message_type: str,
            outcome: str,
            model: str = "nemotron-sample-stub",
            provider: str | None = None,
            latency_ms: float = 0.0,
            details: dict[str, Any] | None = None,
        ) -> None:
            self._step_counter += 1
            prov = provider or (data_provider if agent == "planner" else llm_provider)
            tr = TraceRecord(
                run_id=run_id,
                step=self._step_counter,
                agent=agent,
                message_type=message_type,
                model=model,
                provider=prov,
                degraded=self.is_degraded,
                latency_ms=round(latency_ms, 2),
                retry_count=0,
                outcome=outcome,  # type: ignore
                details=details or {},
            )
            traces.append(tr)
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(tr.model_dump_json() + "\n")

        # ---------------------------------------------------------------------
        # Stage 1: Initial Planning & Extraction
        # ---------------------------------------------------------------------
        t0 = time.perf_counter()
        sources = await asyncio.wait_for(
            self.planner.plan_sources(profile_id), timeout=self.step_timeout_sec
        )
        log_trace(
            agent="planner",
            message_type="plan",
            outcome="success",
            model="extractor-sample-stub",
            latency_ms=(time.perf_counter() - t0) * 1000,
            details={"sources": sources},
        )

        t0 = time.perf_counter()
        fact_ids = await asyncio.wait_for(
            self.extractor.extract_all(profile_id, sources), timeout=self.step_timeout_sec
        )
        log_trace(
            agent="extractor",
            message_type="extracted_facts",
            outcome="success",
            model="extractor-sample-stub",
            latency_ms=(time.perf_counter() - t0) * 1000,
            details={"fact_count": len(fact_ids)},
        )

        # ---------------------------------------------------------------------
        # Stage 2: Cross-Source Entity Linking
        # ---------------------------------------------------------------------
        t0 = time.perf_counter()
        linked_ids = self.linker.link_entities(profile_id)
        log_trace(
            agent="linker",
            message_type="linked_entities",
            outcome="success",
            model="extractor-sample-stub",
            latency_ms=(time.perf_counter() - t0) * 1000,
            details={"linked_entities_count": len(linked_ids)},
        )

        # ---------------------------------------------------------------------
        # Stage 3: Iterative Red-Team & Verifier Loops (max 2 rounds)
        # ---------------------------------------------------------------------
        active_round = 1
        loop_iterations = 0

        while active_round <= self.max_rounds:
            # Step 3A: Red-team formulation / revision
            t0 = time.perf_counter()
            inference_ids = await asyncio.wait_for(
                self.red_team.propose_inferences(profile_id, round_num=active_round),
                timeout=self.step_timeout_sec,
            )
            log_trace(
                agent="red_team",
                message_type="candidate_inference",
                outcome="success",
                model=settings.model_redteam or "nemotron-sample-stub",
                latency_ms=(time.perf_counter() - t0) * 1000,
                details={"round": active_round, "inferences_proposed": len(inference_ids)},
            )

            # Step 3B: Verifier Audit & Feedback
            t0 = time.perf_counter()
            verdicts, evidence_requests, rejected_ids = await asyncio.wait_for(
                self.verifier.verify_inferences(profile_id, round_num=active_round),
                timeout=self.step_timeout_sec,
            )
            all_verdicts.extend(verdicts)

            verifier_outcome = "success"
            if evidence_requests:
                verifier_outcome = "evidence_requested"
            elif rejected_ids:
                verifier_outcome = "rejected"

            log_trace(
                agent="verifier",
                message_type="verdict",
                outcome=verifier_outcome,
                model=settings.model_verifier or "nemotron-sample-stub",
                latency_ms=(time.perf_counter() - t0) * 1000,
                details={
                    "round": active_round,
                    "verdicts_count": len(verdicts),
                    "evidence_requests_count": len(evidence_requests),
                    "rejected_count": len(rejected_ids),
                },
            )

            # --- Feedback Loop 1: Evidence Request -> Planner Query ---
            if evidence_requests:
                loop_iterations += 1
                for req in evidence_requests:
                    t0 = time.perf_counter()
                    new_rows = await self.planner.fulfill_evidence_request(profile_id, req)
                    log_trace(
                        agent="planner",
                        message_type="evidence_query",
                        outcome="success",
                        model="extractor-sample-stub",
                        latency_ms=(time.perf_counter() - t0) * 1000,
                        details={"request_id": req.id, "rows_returned": len(new_rows)},
                    )

                    # Ingest newly queried evidence into World Model and link to inference
                    for r in new_rows:
                        ev_id = self.world_model.ingest(
                            EntityType.FACT.value,
                            {
                                "profile_id": profile_id,
                                "key": "flight_itinerary",
                                "value": f"Flight {r.get('title')} to {r.get('location')} ({r.get('start_time')})",
                                "source_table": req.target_table_or_entity,
                                "source_row_id": str(r.get("event_id")),
                            },
                            source="planner_evidence_fulfillment",
                        )
                        self.world_model.link(
                            ev_id, req.inference_id, RelationType.SUPPORTS.value
                        )

            # --- Feedback Loop 2: Rejections trigger next round revision ---
            if (rejected_ids or evidence_requests) and active_round < self.max_rounds:
                loop_iterations += 1
                active_round += 1
            else:
                # Loop completed or cap reached
                break

        # ---------------------------------------------------------------------
        # Stage 4: Synthesize Final Findings with Evidence Chains
        # ---------------------------------------------------------------------
        raw_inferences = self.world_model.query_entities(
            EntityType.INFERENCE.value, {"profile_id": profile_id}
        )
        for inf in raw_inferences:
            inf_id = inf["_id"]
            chain = self.world_model.evidence_chain(inf_id)
            verdict = next((v for v in all_verdicts if v.inference_id == inf_id), None)
            verdict_label = verdict.label if verdict else VerdictLabel.SPECULATION

            finding = Finding(
                profile_id=profile_id,
                category=inf.get("category", "privacy"),
                claim=inf.get("claim", ""),
                verdict=verdict_label,
                confidence=verdict.confidence if verdict else 0.5,
                attacker_models=[
                    AttackerModel(m) for m in inf.get("attacker_models", [])
                ],
                evidence_chain=chain,
            )
            RiskScorer.score_finding(finding)
            CounterfactualRemovalEngine.evaluate_finding(finding)
            RemediationGenerator.generate_remediation(finding)
            findings.append(finding)

        log_trace(
            agent="reporter",
            message_type="final_report",
            outcome="success",
            details={"findings_count": len(findings), "total_steps": self._step_counter},
        )

        return {
            "run_id": run_id,
            "profile_id": profile_id,
            "findings": findings,
            "verdicts": all_verdicts,
            "traces": traces,
            "trace_file": str(trace_file),
            "rounds_executed": active_round,
            "loop_iterations": loop_iterations,
        }
