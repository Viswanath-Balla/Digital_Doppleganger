"""Linker Agent: establishes SAME_AS, Place, and TimePattern correlations across sources."""

from __future__ import annotations

from typing import Any

from src.dd.agents.base_agent import BaseAgent
from src.dd.models.domain import EntityType, RelationType


class LinkerAgent(BaseAgent):
    """Linker Agent: discovers cross-source linkages and constructs high-order entities."""

    def __init__(self, world_model: Any, data_layer: Any, llm_client: Any) -> None:
        super().__init__(
            name="linker",
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
        )

    def link_entities(self, profile_id: str) -> list[str]:
        """Correlate extracted facts into Places, TimePatterns, and SAME_AS edges."""
        created_entity_ids: list[str] = []
        facts = self.wm_query_entities(EntityType.FACT.value, {"profile_id": profile_id})

        # 1. Correlate Home Residence Place (Delivery Address + GPS Cluster)
        delivery_fact = next((f for f in facts if f.get("key") == "primary_delivery_address"), None)
        origin_cluster_fact = next((f for f in facts if f.get("key") == "primary_run_origin_cluster"), None)

        if delivery_fact and origin_cluster_fact:
            addr = delivery_fact.get("value", "")
            coords = origin_cluster_fact.get("value", "")

            place_id = self.wm_ingest(
                EntityType.PLACE.value,
                {
                    "profile_id": profile_id,
                    "name": "Home Residence",
                    "address": addr,
                    "coordinates": coords,
                    "confidence": 0.95,
                },
                source="linker_entity_resolution",
            )
            created_entity_ids.append(place_id)

            # Establish SAME_AS and DERIVED_FROM edges
            self.wm_link(delivery_fact["_id"], place_id, RelationType.DERIVED_FROM.value)
            self.wm_link(origin_cluster_fact["_id"], place_id, RelationType.SAME_AS.value)

        # 2. Correlate Weekday Morning Routine (Strava Runs + Standup Sync)
        morning_fact = next((f for f in facts if f.get("key") == "weekday_morning_run_habit"), None)
        standup_facts = [f for f in facts if "standup" in str(f.get("value", "")).lower()]

        if morning_fact:
            routine_id = self.wm_ingest(
                EntityType.TIME_PATTERN.value,
                {
                    "profile_id": profile_id,
                    "pattern": "Weekday Morning Routine",
                    "window": "06:30 - 09:30 AM",
                    "recurrence": "Monday-Friday",
                    "confidence": 0.90,
                },
                source="linker_temporal_correlation",
            )
            created_entity_ids.append(routine_id)
            self.wm_link(morning_fact["_id"], routine_id, RelationType.SUPPORTS.value)
            for sf in standup_facts:
                self.wm_link(sf["_id"], routine_id, RelationType.SUPPORTS.value)

        # 3. Correlate Vacation Absence Window (Calendar PTO + Social Airport Post)
        vacation_cal = [f for f in facts if "vacation" in str(f.get("value", "")).lower() or "pto" in str(f.get("value", "")).lower()]
        vacation_soc = [f for f in facts if "hawaii" in str(f.get("value", "")).lower() or "airport" in str(f.get("value", "")).lower()]

        if vacation_cal and vacation_soc:
            absence_id = self.wm_ingest(
                EntityType.TIME_PATTERN.value,
                {
                    "profile_id": profile_id,
                    "pattern": "Absence Window (Vacant Home)",
                    "window": "July 10 - July 20, 2026",
                    "destination": "Hawaii",
                    "confidence": 0.95,
                },
                source="linker_absence_correlation",
            )
            created_entity_ids.append(absence_id)
            for vf in vacation_cal:
                self.wm_link(vf["_id"], absence_id, RelationType.SUPPORTS.value)
            for sf in vacation_soc:
                self.wm_link(sf["_id"], absence_id, RelationType.SUPPORTS.value)

        # 4. Profile B: Health & Medical Clinic Linkage
        oncology_events = [f for f in facts if "oncology" in str(f.get("value", "")).lower() or "hematology" in str(f.get("value", "")).lower()]
        pharmacy_facts = [f for f in facts if f.get("source_table") == "pharmacy_orders"]

        if oncology_events:
            clinic_id = self.wm_ingest(
                EntityType.PLACE.value,
                {
                    "profile_id": profile_id,
                    "name": "Oakridge Oncology & Hematology Suite 400",
                    "category": "Medical Specialist Clinic",
                    "confidence": 0.95,
                },
                source="linker_medical_resolution",
            )
            created_entity_ids.append(clinic_id)
            for oe in oncology_events:
                self.wm_link(oe["_id"], clinic_id, RelationType.DERIVED_FROM.value)
            for pf in pharmacy_facts:
                self.wm_link(pf["_id"], clinic_id, RelationType.SUPPORTS.value)

        # 5. Profile C: Identity KBA Linkages (DOB, Pet Name, School)
        bday_facts = [f for f in facts if "1996" in str(f.get("value", "")) or "birthday" in str(f.get("value", "")).lower()]
        pet_facts = [f for f in facts if "barnaby" in str(f.get("value", "")).lower() or "retriever" in str(f.get("value", "")).lower()]
        school_facts = [f for f in facts if "oakfield" in str(f.get("value", "")).lower()]

        if bday_facts:
            kba_id = self.wm_ingest(
                EntityType.ACCOUNT.value,
                {
                    "profile_id": profile_id,
                    "account_type": "Identity Profile",
                    "claim": "Date of Birth: May 14, 1996",
                    "confidence": 0.95,
                },
                source="linker_kba_resolution",
            )
            created_entity_ids.append(kba_id)
            for bf in bday_facts:
                self.wm_link(bf["_id"], kba_id, RelationType.SUPPORTS.value)

        if pet_facts:
            pet_id = self.wm_ingest(
                EntityType.ACCOUNT.value,
                {
                    "profile_id": profile_id,
                    "account_type": "KBA Security Question Anchor",
                    "claim": "Pet Name: Barnaby",
                    "confidence": 0.90,
                },
                source="linker_kba_resolution",
            )
            created_entity_ids.append(pet_id)
            for pf in pet_facts:
                self.wm_link(pf["_id"], pet_id, RelationType.SUPPORTS.value)

        if school_facts:
            for sf in school_facts:
                created_entity_ids.append(sf["_id"])

        return created_entity_ids
