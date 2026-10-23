"""In-memory World Model implementation.

Provides idempotent entity ingestion (content-hash based), directed
relationships with provenance, and BFS-based evidence-chain traversal.

Phase 2 will flesh this out after reading the Meterless World Model docs.
This version is enough to satisfy the interface contract and pass tests.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from src.dd.adapters.base import WorldModel


def _content_hash(entity_type: str, data: dict[str, Any]) -> str:
    """Deterministic hash of entity type + sorted data for idempotent ingest."""
    canonical = json.dumps({"type": entity_type, **data}, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class SampleWorldModel(WorldModel):
    """In-memory World Model backed by Python dicts.

    Entities are keyed by a content-hash so ingesting the same data twice
    returns the same id without creating duplicates.
    """

    def __init__(self) -> None:
        # entity_id -> entity dict (includes _type, _source, _created, _version, + data)
        self._entities: dict[str, dict[str, Any]] = {}
        # list of (from_id, to_id, relation, metadata)
        self._relations: list[tuple[str, str, str, dict[str, Any]]] = []
        # entity_id -> list of historical versions
        self._versions: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # WorldModel interface
    # ------------------------------------------------------------------

    def ingest(self, entity_type: str, data: dict[str, Any], source: str) -> str:
        """Idempotently insert an entity; return its stable id."""
        eid = _content_hash(entity_type, data)

        if eid in self._entities:
            # Already exists — bump version if source differs
            existing = self._entities[eid]
            if source not in existing.get("_sources", []):
                existing.setdefault("_sources", []).append(source)
                existing["_version"] = existing.get("_version", 1) + 1
                self._versions.setdefault(eid, []).append(
                    {**existing, "_updated": datetime.now(timezone.utc).isoformat()}
                )
            return eid

        entity = {
            "_id": eid,
            "_type": entity_type,
            "_source": source,
            "_sources": [source],
            "_created": datetime.now(timezone.utc).isoformat(),
            "_version": 1,
            **data,
        }
        self._entities[eid] = entity
        self._versions[eid] = [entity.copy()]
        return eid

    def get(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity by id."""
        return self._entities.get(entity_id)

    def link(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a directed relationship."""
        if from_id not in self._entities:
            raise KeyError(f"Entity not found: {from_id}")
        if to_id not in self._entities:
            raise KeyError(f"Entity not found: {to_id}")
        self._relations.append((from_id, to_id, relation, metadata or {}))

    def evidence_chain(self, entity_id: str) -> list[dict[str, Any]]:
        """BFS walk of SUPPORTS / DERIVED_FROM edges back to leaf facts.

        Returns entities ordered root-first (leaf facts first, target last).
        """
        if entity_id not in self._entities:
            return []

        visited: set[str] = set()
        queue: list[str] = [entity_id]
        chain: list[dict[str, Any]] = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            entity = self._entities.get(current)
            if entity:
                chain.append(entity)
            # Follow SUPPORTS and DERIVED_FROM edges (to_id -> from_id direction)
            for from_id, to_id, relation, _meta in self._relations:
                if to_id == current and relation in ("SUPPORTS", "DERIVED_FROM"):
                    if from_id not in visited:
                        queue.append(from_id)

        # Reverse so leaf facts come first
        chain.reverse()
        return chain

    def query_entities(
        self,
        entity_type: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """List entities of a type, optionally filtered by field values."""
        results = []
        for entity in self._entities.values():
            if entity.get("_type") != entity_type:
                continue
            if filters:
                if all(entity.get(k) == v for k, v in filters.items()):
                    results.append(entity)
            else:
                results.append(entity)
        return results
