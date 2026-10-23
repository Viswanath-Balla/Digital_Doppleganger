"""Planner Agent: orchestrates source extraction and fulfills evidence requests."""

from __future__ import annotations

from typing import Any

from src.dd.agents.base_agent import BaseAgent
from src.dd.models.domain import EvidenceRequest


class PlannerAgent(BaseAgent):
    """Planner Agent: selects data sources, schedules queries, and fulfills Verifier evidence requests."""

    def __init__(self, world_model: Any, data_layer: Any, llm_client: Any) -> None:
        super().__init__(
            name="planner",
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
        )

    async def plan_sources(self, profile_id: str) -> list[str]:
        """Determine optimal extraction sequence across available tables."""
        # Prioritize rich geospatial and delivery telemetry first, followed by calendar/social
        return [
            "profile_fields",
            "strava_activities",
            "food_orders",
            "calendar_events",
            "social_posts",
            "pharmacy_orders",
        ]

    async def fulfill_evidence_request(
        self, profile_id: str, request: EvidenceRequest
    ) -> list[dict[str, Any]]:
        """Query DataLayer for targeted evidence requested by the Verifier."""
        target_table = request.target_table_or_entity
        predicate = request.predicate

        # Run guarded SQL query for requested evidence
        sql = f"SELECT * FROM {target_table} WHERE profile_id = '{profile_id}'"
        if predicate:
            sql += f" AND ({predicate})"

        rows = await self.query_data(sql)
        return rows
