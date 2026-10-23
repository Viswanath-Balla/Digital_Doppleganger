"""Abstract base interfaces for DataLayer, LLMClient, and WorldModel.

All agents interact with external systems ONLY through these interfaces.
Implementations are swapped via configuration (sample vs. live).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared response model for LLM calls
# ---------------------------------------------------------------------------

class LLMResponse(BaseModel):
    """Standard response from any LLMClient implementation."""

    content: str
    model: str
    latency_ms: float = 0.0
    retries: int = 0
    raw: dict = Field(default_factory=dict, exclude=True)


# ---------------------------------------------------------------------------
# DataLayer — all data access goes through SQL
# ---------------------------------------------------------------------------

class DataLayer(ABC):
    """Abstract data-access layer.  Agents get data ONLY through this."""

    @abstractmethod
    async def query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute *sql* with optional bind *params*; return rows as dicts."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the backing store is reachable."""


# ---------------------------------------------------------------------------
# LLMClient — every LLM call goes through this
# ---------------------------------------------------------------------------

class LLMClient(ABC):
    """Abstract LLM client.  Implementations handle retries and timeouts."""

    @abstractmethod
    async def complete(
        self,
        agent: str,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Send a chat-completion request and return a typed response.

        Parameters
        ----------
        agent:
            Logical agent name (e.g. ``"red_team"``), used for logging and
            model routing.
        messages:
            OpenAI-style message list (``[{"role": ..., "content": ...}]``).
        response_schema:
            Optional Pydantic model.  Implementations may use this for
            structured/JSON-mode output.
        """


# ---------------------------------------------------------------------------
# WorldModel — shared agent state (entities, relationships, provenance)
# ---------------------------------------------------------------------------

class WorldModel(ABC):
    """Abstract World Model engine — the shared knowledge graph.

    Entity types: Person, Place, TimePattern, Account, Fact, Inference,
    Evidence.  Relation types: SUPPORTS, DERIVED_FROM, SAME_AS, CONTRADICTS.
    """

    @abstractmethod
    def ingest(self, entity_type: str, data: dict[str, Any], source: str) -> str:
        """Idempotently insert an entity; return its stable id.

        If an entity with the same content-hash already exists, return the
        existing id without creating a duplicate.
        """

    @abstractmethod
    def get(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity by id, or None if not found."""

    @abstractmethod
    def link(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a directed relationship between two entities."""

    @abstractmethod
    def evidence_chain(self, entity_id: str) -> list[dict[str, Any]]:
        """Walk SUPPORTS / DERIVED_FROM edges back to source rows.

        Returns a list of entities from the target back to leaf facts,
        ordered root-first.
        """

    @abstractmethod
    def query_entities(
        self,
        entity_type: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """List entities of *entity_type*, optionally filtered by field values."""
