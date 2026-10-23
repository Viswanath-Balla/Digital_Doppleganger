"""Sponsor Tech Proof Tests: Meterless World Model Engine.

These 4 tests serve as verifiable evidence that the Meterless World Model engine
correctly implements:
  1. Idempotent ingestion (same fact twice yields 1 entity with stable id)
  2. Provenance preservation across conflicting multi-source facts
  3. Full evidence chain walk from inference back to raw source rows
  4. Inter-agent shared state (Red-team writes, Verifier reads & updates)
"""

from __future__ import annotations

import pytest

from src.dd.adapters.meterless_world_model import MeterlessWorldModel
from src.dd.models.domain import (
    AttackerModel,
    EntityType,
    Fact,
    Inference,
    RelationType,
    Verdict,
    VerdictLabel,
)


@pytest.fixture
def wm() -> MeterlessWorldModel:
    """Fixture providing a fresh MeterlessWorldModel engine instance."""
    return MeterlessWorldModel()


class TestMeterlessWorldModelSponsorProofs:
    """Mandatory proof tests cited in hackathon submission."""

    def test_ingesting_same_fact_twice_yields_one_entity(
        self, wm: MeterlessWorldModel
    ) -> None:
        """Proof 1: Ingesting the same fact twice yields one entity with identical ID."""
        fact_payload = {
            "profile_id": "A",
            "key": "home_address",
            "value": "742 Evergreen Terr, Springfield",
            "source_table": "food_orders",
        }

        # First ingestion
        id_1 = wm.ingest(EntityType.FACT.value, fact_payload, source="food_orders")
        # Second ingestion with identical content
        id_2 = wm.ingest(EntityType.FACT.value, fact_payload, source="food_orders")

        # Stable ID must match
        assert id_1 == id_2

        # Exactly 1 entity must exist in the world model
        entities = wm.query_entities(EntityType.FACT.value)
        assert len(entities) == 1
        assert entities[0]["_id"] == id_1
        assert entities[0]["_version"] == 1
        assert entities[0]["_sources"] == ["food_orders"]

    def test_conflicting_facts_from_different_sources_both_keep_provenance(
        self, wm: MeterlessWorldModel
    ) -> None:
        """Proof 2: Two conflicting facts from different sources both keep provenance and link."""
        # Source 1: Strava activities indicates Springfield home
        fact_strava = {
            "profile_id": "A",
            "key": "residence_city",
            "value": "Springfield",
            "source_table": "strava_activities",
        }
        id_strava = wm.ingest(EntityType.FACT.value, fact_strava, source="strava_crawler")

        # Source 2: Old social post claims Seattle residence
        fact_social = {
            "profile_id": "A",
            "key": "residence_city",
            "value": "Seattle",
            "source_table": "social_posts",
        }
        id_social = wm.ingest(EntityType.FACT.value, fact_social, source="social_crawler")

        # Both entities must exist independently (neither is lost or overwritten)
        assert id_strava != id_social
        ent_strava = wm.get(id_strava)
        ent_social = wm.get(id_social)

        assert ent_strava is not None
        assert ent_social is not None
        assert ent_strava["value"] == "Springfield"
        assert ent_social["value"] == "Seattle"

        # Provenance must be intact for each
        assert ent_strava["_sources"] == ["strava_crawler"]
        assert ent_social["_sources"] == ["social_crawler"]

        # CONTRADICTS relation must be automatically established
        contradictions = wm.get_contradictions(profile_id="A")
        assert len(contradictions) >= 1
        edge_data = contradictions[0]
        assert (
            edge_data["entity_1"]["_id"] == id_strava
            and edge_data["entity_2"]["_id"] == id_social
        ) or (
            edge_data["entity_1"]["_id"] == id_social
            and edge_data["entity_2"]["_id"] == id_strava
        )

    def test_inference_returns_full_evidence_chain_to_source_rows(
        self, wm: MeterlessWorldModel
    ) -> None:
        """Proof 3: Any inference returns its full evidence chain back to source rows."""
        # 1. Ingest raw source row facts
        fact_order_id = wm.ingest(
            EntityType.FACT.value,
            {
                "profile_id": "A",
                "key": "food_delivery_target",
                "value": "742 Evergreen Terr",
                "source_table": "food_orders",
                "source_row_id": "ORD_A01",
            },
            source="food_orders",
        )

        fact_strava_id = wm.ingest(
            EntityType.FACT.value,
            {
                "profile_id": "A",
                "key": "running_cluster_origin",
                "value": "39.7817, -89.6501",
                "source_table": "strava_activities",
                "source_row_id": "STR_A01",
            },
            source="strava_activities",
        )

        # 2. Ingest derived Place entity and link facts
        place_id = wm.ingest(
            EntityType.PLACE.value,
            {
                "profile_id": "A",
                "name": "Home Residence",
                "address": "742 Evergreen Terr, Springfield",
            },
            source="linker_agent",
        )
        wm.link(fact_order_id, place_id, RelationType.DERIVED_FROM.value)
        wm.link(fact_strava_id, place_id, RelationType.SAME_AS.value)

        # 3. Red-team proposes privacy inference
        inference_id = wm.ingest(
            EntityType.INFERENCE.value,
            {
                "profile_id": "A",
                "claim": "Subject resides at 742 Evergreen Terr, Springfield",
                "category": "location",
                "attacker_models": [AttackerModel.STALKER.value, AttackerModel.BURGLAR.value],
            },
            source="red_team_agent",
        )
        wm.link(place_id, inference_id, RelationType.SUPPORTS.value)

        # 4. Request full evidence chain from the Inference node
        chain = wm.evidence_chain(inference_id)

        # Must traverse: Raw Facts -> Place -> Inference
        chain_ids = [node["_id"] for node in chain]
        assert inference_id in chain_ids
        assert place_id in chain_ids
        assert fact_order_id in chain_ids
        assert fact_strava_id in chain_ids

        # Root facts must appear first (root-first ordering)
        assert chain[-1]["_id"] == inference_id
        assert chain_ids.index(fact_order_id) < chain_ids.index(inference_id)
        assert chain_ids.index(fact_strava_id) < chain_ids.index(inference_id)

    def test_inter_agent_shared_state_simulation(
        self, wm: MeterlessWorldModel
    ) -> None:
        """Proof 4: Record written by one agent is read and updated by another agent."""
        profile_id = "A"

        # Step A: Extractor agent extracts two facts into the shared World Model
        f1_id = wm.ingest(
            EntityType.FACT.value,
            {"profile_id": profile_id, "key": "daily_standup_time", "value": "09:30 AM", "source_table": "calendar_events"},
            source="extractor_agent",
        )
        f2_id = wm.ingest(
            EntityType.FACT.value,
            {"profile_id": profile_id, "key": "running_start_time", "value": "06:30 AM", "source_table": "strava_activities"},
            source="extractor_agent",
        )

        # Step B: Red-team agent inspects World Model and proposes an Inference
        facts_seen = wm.query_entities(EntityType.FACT.value, {"profile_id": profile_id})
        assert len(facts_seen) == 2

        inf_id = wm.ingest(
            EntityType.INFERENCE.value,
            {
                "profile_id": profile_id,
                "claim": "Predictable weekday morning routine between 06:30 and 09:30 AM",
                "category": "routine",
                "status": "proposed",
            },
            source="red_team_agent",
        )
        wm.link(f1_id, inf_id, RelationType.SUPPORTS.value, created_by="red_team_agent")
        wm.link(f2_id, inf_id, RelationType.SUPPORTS.value, created_by="red_team_agent")

        # Step C: Verifier agent reads pending inferences from the shared World Model
        pending_inferences = wm.query_entities(
            EntityType.INFERENCE.value, {"profile_id": profile_id, "status": "proposed"}
        )
        assert len(pending_inferences) == 1
        target_inf = pending_inferences[0]
        assert target_inf["_id"] == inf_id

        # Verifier checks supporting evidence chain from the World Model
        supporting_chain = wm.evidence_chain(target_inf["_id"])
        assert len(supporting_chain) == 3  # [f1, f2, inf]

        # Verifier approves and writes a Verdict into the World Model
        verdict_id = wm.ingest(
            EntityType.EVIDENCE.value,
            {
                "profile_id": profile_id,
                "inference_id": inf_id,
                "verdict_label": VerdictLabel.SUPPORTED.value,
                "confidence": 0.95,
                "rationale": "Direct temporal correlation between athletic telemetry and calendar standup.",
            },
            source="verifier_agent",
        )
        wm.link(verdict_id, inf_id, RelationType.SUPPORTS.value, created_by="verifier_agent")

        # Update status of inference to verified
        wm.ingest(
            EntityType.INFERENCE.value,
            {
                "id": inf_id,
                "profile_id": profile_id,
                "claim": target_inf["claim"],
                "category": target_inf["category"],
                "status": "verified",
            },
            source="verifier_agent",
        )

        # Step D: Confirm final verified state is accessible to downstream Reporter
        verified_ent = wm.get(inf_id)
        assert verified_ent is not None
        assert verified_ent["status"] == "verified"
        assert verified_ent["_version"] == 2  # Updated from v1 to v2
        assert "red_team_agent" in verified_ent["_sources"]
        assert "verifier_agent" in verified_ent["_sources"]

    def test_provenance_validation_rejects_empty_source(
        self, wm: MeterlessWorldModel
    ) -> None:
        """Meterless Spec §4.1: No provenance -> rejected."""
        with pytest.raises(ValueError, match="Provenance check failed"):
            wm.ingest(
                EntityType.FACT.value,
                {"profile_id": "A", "key": "k", "value": "v"},
                source="",
            )

    def test_context_builder_formats_profile_context(
        self, wm: MeterlessWorldModel
    ) -> None:
        """Meterless Spec §7: Context builder packs entities into prompt-ready block."""
        wm.ingest(
            EntityType.FACT.value,
            {"profile_id": "A", "key": "job_title", "value": "Senior Engineer"},
            source="linkedin",
        )
        wm.ingest(
            EntityType.PLACE.value,
            {"profile_id": "A", "name": "Office", "address": "100 Innovation Way"},
            source="linker",
        )
        wm.ingest(
            EntityType.INFERENCE.value,
            {"profile_id": "A", "claim": "Works at tech park", "category": "employment", "status": "proposed"},
            source="red_team",
        )

        ctx = wm.build_context(profile_id="A")
        assert "WORLD MODEL CONTEXT: PROFILE A" in ctx
        assert "[linkedin] job_title: Senior Engineer" in ctx
        assert "Office: 100 Innovation Way" in ctx
        assert "Works at tech park" in ctx

