"""Base agent class with guarded tool access."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.dd.adapters.base import DataLayer, LLMClient, LLMResponse, WorldModel
from src.dd.agents.prompt_loader import PromptInfo, get_prompt
from src.dd.guard.tool_guard import guard_tool_call


class BaseAgent:
    """Base class for all audit agents.

    Enforces the security allowlist guard on every data, LLM, and World Model operation.
    """

    def __init__(
        self,
        name: str,
        world_model: WorldModel,
        data_layer: DataLayer,
        llm_client: LLMClient,
    ) -> None:
        self.name = name
        self.world_model = world_model
        self.data_layer = data_layer
        self.llm_client = llm_client
        self.prompt_info: PromptInfo = get_prompt(self.name)

    @property
    def system_prompt(self) -> str:
        """System prompt content loaded from markdown prompt file."""
        return self.prompt_info.content

    async def query_data(
        self, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Guarded execution of SQL queries against DataLayer."""
        guard_tool_call("sql_query")
        return await self.data_layer.query(sql, params)

    async def complete_llm(
        self,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Guarded completion call via LLMClient."""
        guard_tool_call("llm_complete")
        return await self.llm_client.complete(
            agent=self.name,
            messages=messages,
            response_schema=response_schema,
        )

    def wm_ingest(self, entity_type: str, data: dict[str, Any], source: str) -> str:
        """Guarded entity ingestion into World Model."""
        guard_tool_call("world_model_write")
        return self.world_model.ingest(entity_type, data, source)

    def wm_link(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Guarded relation creation in World Model."""
        guard_tool_call("world_model_write")
        self.world_model.link(from_id, to_id, relation, metadata)

    def wm_get(self, entity_id: str) -> dict[str, Any] | None:
        """Guarded retrieval from World Model."""
        guard_tool_call("world_model_read")
        return self.world_model.get(entity_id)

    def wm_query_entities(
        self, entity_type: str, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Guarded entity search in World Model."""
        guard_tool_call("world_model_read")
        return self.world_model.query_entities(entity_type, filters)

    def wm_evidence_chain(self, entity_id: str) -> list[dict[str, Any]]:
        """Guarded evidence chain walk in World Model."""
        guard_tool_call("world_model_read")
        return self.world_model.evidence_chain(entity_id)
