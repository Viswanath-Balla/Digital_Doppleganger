"""Meterless World Model engine implementation.

Provides the shared multi-agent knowledge graph with:
  - Stable content-addressed entity IDs
  - Idempotent ingestion
  - Multi-source provenance on every record
  - Immutable versioned update history
  - Typed directed relations (SUPPORTS, DERIVED_FROM, SAME_AS, CONTRADICTS)
  - BFS evidence chain traversal
  - Rebuildable derived profile & contradiction views
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from datetime import datetime, timezone
from typing import Any

from src.dd.adapters.base import WorldModel
from src.dd.models.domain import EntityType, RelationType


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_stable_id(entity_type: str, data: dict[str, Any]) -> str:
    """Generate a stable, deterministic content-addressed identifier.

    Uses primary identifying keys if present (e.g. profile_id, key, activity_id),
    otherwise serializes the normalized dictionary.
    """
    type_prefix = entity_type.lower()[:4]

    # Prioritize natural keys when available
    if "id" in data and data["id"]:
        return str(data["id"])

    # For Fact entities: hash profile_id + key + value + source_table
    if entity_type == EntityType.FACT.value or entity_type == "Fact":
        core = {
            "profile_id": str(data.get("profile_id", "")),
            "key": str(data.get("key", "")),
            "value": str(data.get("value", "")),
            "source_table": str(data.get("source_table", "")),
        }
    elif entity_type == EntityType.INFERENCE.value or entity_type == "Inference":
        core = {
            "profile_id": str(data.get("profile_id", "")),
            "claim": str(data.get("claim", "")),
            "category": str(data.get("category", "")),
        }
    elif entity_type == EntityType.PLACE.value or entity_type == "Place":
        core = {
            "profile_id": str(data.get("profile_id", "")),
            "name": str(data.get("name", "")),
            "address": str(data.get("address", "")),
        }
    elif entity_type == EntityType.TIME_PATTERN.value or entity_type == "TimePattern":
        core = {
            "profile_id": str(data.get("profile_id", "")),
            "pattern": str(data.get("pattern", "")),
            "window": str(data.get("window", "")),
        }
    else:
        # Fallback to normalized dictionary content
        core = {k: v for k, v in data.items() if not k.startswith("_")}

    raw = json.dumps(core, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"{type_prefix}_{digest}"


class MeterlessWorldModel(WorldModel):
    """Production implementation of the Meterless World Model engine."""

    def __init__(self) -> None:
        # entity_id -> entity dict
        self._entities: dict[str, dict[str, Any]] = {}
        # entity_id -> list of historical version snapshots
        self._history: dict[str, list[dict[str, Any]]] = {}
        # list of directed edges: {from_id, to_id, relation, metadata, created_at, created_by}
        self._edges: list[dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Ingest & Storage
    # -------------------------------------------------------------------------

    def ingest(self, entity_type: str, data: dict[str, Any], source: str) -> str:
        """Idempotently ingest an entity.

        Enforces Meterless World Model invariant §4.1:
          - Provenance check: every record must declare its source.
        """
        if not source or not str(source).strip():
            raise ValueError(
                "Provenance check failed: 'source' is mandatory for every World Model entity."
            )

        entity_id = _generate_stable_id(entity_type, data)
        now = _utc_now_str()

        if entity_id in self._entities:
            existing = self._entities[entity_id]
            # Update source provenance
            sources = existing.get("_sources", [])
            if source not in sources:
                sources.append(source)
                existing["_sources"] = sources

            # Check if any non-metadata field changed
            has_changes = False
            for k, v in data.items():
                if not k.startswith("_") and existing.get(k) != v:
                    existing[k] = v
                    has_changes = True

            if has_changes:
                existing["_version"] = existing.get("_version", 1) + 1
                existing["_updated_at"] = now
                self._history[entity_id].append(existing.copy())

            return entity_id

        # New entity creation
        record = {
            "_id": entity_id,
            "_type": entity_type,
            "_source": source,
            "_sources": [source],
            "_created_by": source,
            "_created_at": now,
            "_updated_at": now,
            "_version": 1,
            **{k: v for k, v in data.items() if not k.startswith("_")},
        }
        self._entities[entity_id] = record
        self._history[entity_id] = [record.copy()]

        # Auto-detect contradiction with existing facts
        self._check_and_link_contradictions(entity_id, record)

        return entity_id

    def get(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity by id, returning a copy."""
        ent = self._entities.get(entity_id)
        return ent.copy() if ent else None

    def get_history(self, entity_id: str) -> list[dict[str, Any]]:
        """Return the immutable audit history of changes for an entity."""
        return [item.copy() for item in self._history.get(entity_id, [])]

    # -------------------------------------------------------------------------
    # Relations & Graph Links
    # -------------------------------------------------------------------------

    def link(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        metadata: dict[str, Any] | None = None,
        created_by: str = "system",
    ) -> None:
        """Create a directed relationship between two entities."""
        if from_id not in self._entities:
            raise KeyError(f"WorldModel entity not found: {from_id}")
        if to_id not in self._entities:
            raise KeyError(f"WorldModel entity not found: {to_id}")

        edge = {
            "from_id": from_id,
            "to_id": to_id,
            "relation": relation,
            "metadata": metadata or {},
            "created_by": created_by,
            "created_at": _utc_now_str(),
        }

        # Avoid duplicate identical edges
        for existing in self._edges:
            if (
                existing["from_id"] == from_id
                and existing["to_id"] == to_id
                and existing["relation"] == relation
            ):
                return

        self._edges.append(edge)

    def get_edges(
        self,
        from_id: str | None = None,
        to_id: str | None = None,
        relation: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query edges with optional filters."""
        results = []
        for e in self._edges:
            if from_id and e["from_id"] != from_id:
                continue
            if to_id and e["to_id"] != to_id:
                continue
            if relation and e["relation"] != relation:
                continue
            results.append(e.copy())
        return results

    # -------------------------------------------------------------------------
    # Evidence Chain Traversal
    # -------------------------------------------------------------------------

    def evidence_chain(self, entity_id: str) -> list[dict[str, Any]]:
        """Resolve full evidence lineage back to raw source facts.

        Follows SUPPORTS, DERIVED_FROM, and SAME_AS edges in reverse (from inference
        back to facts). Returns the lineage ordered root-first (leaf facts -> target).
        """
        if entity_id not in self._entities:
            return []

        visited: set[str] = set()
        queue: deque[str] = deque([entity_id])
        chain: list[dict[str, Any]] = []

        while queue:
            current_id = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)

            node = self._entities.get(current_id)
            if node:
                chain.append(node.copy())

            # Find upstream supporting entities
            # e.g., (from_fact) --SUPPORTS--> (to_inference)
            # e.g., (from_source_row) --DERIVED_FROM--> (to_fact)
            # e.g., (from_entity) --SAME_AS--> (to_entity)
            for edge in self._edges:
                rel = edge["relation"]
                if rel in (
                    RelationType.SUPPORTS.value,
                    RelationType.DERIVED_FROM.value,
                    RelationType.SAME_AS.value,
                    "SUPPORTS",
                    "DERIVED_FROM",
                    "SAME_AS",
                ):
                    if edge["to_id"] == current_id and edge["from_id"] not in visited:
                        queue.append(edge["from_id"])

        # Reverse so root evidence / raw facts appear first, synthesized inference last
        chain.reverse()
        return chain

    # -------------------------------------------------------------------------
    # Entity Queries & Derived Views
    # -------------------------------------------------------------------------

    def query_entities(
        self,
        entity_type: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """List entities matching entity_type and optional field filter."""
        results = []
        for ent in self._entities.values():
            if ent.get("_type") != entity_type:
                continue
            if filters:
                if all(ent.get(k) == v for k, v in filters.items()):
                    results.append(ent.copy())
            else:
                results.append(ent.copy())
        return results

    def get_profile_view(self, profile_id: str) -> dict[str, Any]:
        """Generate a unified derived view of all knowledge for a profile."""
        facts = self.query_entities("Fact", {"profile_id": profile_id})
        inferences = self.query_entities("Inference", {"profile_id": profile_id})
        places = self.query_entities("Place", {"profile_id": profile_id})
        time_patterns = self.query_entities("TimePattern", {"profile_id": profile_id})

        return {
            "profile_id": profile_id,
            "fact_count": len(facts),
            "inference_count": len(inferences),
            "facts": facts,
            "inferences": inferences,
            "places": places,
            "time_patterns": time_patterns,
            "contradiction_count": len(self.get_contradictions(profile_id)),
        }

    def get_contradictions(self, profile_id: str | None = None) -> list[dict[str, Any]]:
        """Return all entity pairs linked by a CONTRADICTS relation."""
        contradictions = []
        for edge in self._edges:
            if edge["relation"] in (RelationType.CONTRADICTS.value, "CONTRADICTS"):
                e1 = self._entities.get(edge["from_id"])
                e2 = self._entities.get(edge["to_id"])
                if e1 and e2:
                    if profile_id:
                        if e1.get("profile_id") != profile_id and e2.get("profile_id") != profile_id:
                            continue
                    contradictions.append({
                        "entity_1": e1.copy(),
                        "entity_2": e2.copy(),
                        "metadata": edge.get("metadata", {}),
                    })
        return contradictions

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def build_context(
        self, profile_id: str, max_entities: int = 50
    ) -> str:
        """Read Surface Context Builder: Pack entities and relations into a concise prompt block.

        Adheres to Meterless World Model read surface specification §7:
          - Formats facts, places, and time patterns with provenance within a budget.
        """
        view = self.get_profile_view(profile_id)
        lines = [f"=== WORLD MODEL CONTEXT: PROFILE {profile_id} ==="]

        facts = view["facts"][:max_entities]
        if facts:
            lines.append("## Known Facts & Attributes:")
            for f in facts:
                src = f.get("_source", "unknown")
                lines.append(f"  - [{src}] {f.get('key')}: {f.get('value')}")

        places = view["places"]
        if places:
            lines.append("## Correlated Places:")
            for p in places:
                lines.append(f"  - {p.get('name')}: {p.get('address', '')}")

        patterns = view["time_patterns"]
        if patterns:
            lines.append("## Inferred Routine & Patterns:")
            for pt in patterns:
                lines.append(f"  - {pt.get('pattern')}: {pt.get('window', '')}")

        inferences = view["inferences"]
        if inferences:
            lines.append("## Active Inferences / Hypotheses:")
            for inf in inferences:
                status = inf.get("status", "proposed")
                lines.append(f"  - [{status.upper()}] {inf.get('claim')} (category: {inf.get('category')})")

        return "\n".join(lines)

    def _check_and_link_contradictions(
        self, new_id: str, new_entity: dict[str, Any]
    ) -> None:
        """Detect and link contradictory facts without dropping either record."""
        if new_entity.get("_type") not in ("Fact", EntityType.FACT.value):
            return

        pid = new_entity.get("profile_id")
        key = new_entity.get("key")
        val = new_entity.get("value")

        if not pid or not key:
            return

        for existing_id, existing in self._entities.items():
            if existing_id == new_id:
                continue
            if (
                existing.get("_type") in ("Fact", EntityType.FACT.value)
                and existing.get("profile_id") == pid
                and existing.get("key") == key
                and existing.get("value") != val
            ):
                # Link conflicting facts with CONTRADICTS relation
                self.link(
                    from_id=existing_id,
                    to_id=new_id,
                    relation=RelationType.CONTRADICTS.value,
                    metadata={"reason": f"Discrepancy in key '{key}': '{existing.get('value')}' vs '{val}'"},
                    created_by="world_model_engine",
                )
