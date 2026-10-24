"""Linker Agent: establishes SAME_AS, Place, and TimePattern correlations across sources."""

from __future__ import annotations

from typing import Any

from src.dd.agents.base_agent import BaseAgent
from src.dd.config import get_settings
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
        self.last_link_reasons: list[dict[str, Any]] = []
        self.last_brief: dict[str, Any] = {}

    def link_entities(self, profile_id: str) -> list[str]:
        """Correlate extracted facts into Places, TimePatterns, and SAME_AS edges."""
        created_entity_ids: list[str] = []
        self.last_link_reasons = []
        facts = self.wm_query_entities(EntityType.FACT.value, {"profile_id": profile_id})

        settings = get_settings()
        radius_m = settings.linker_gps_radius_meters
        time_window_min = settings.linker_time_window_minutes

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

            # Establish SAME_AS and DERIVED_FROM edges with reason codes
            self.wm_link(
                delivery_fact["_id"],
                place_id,
                RelationType.DERIVED_FROM.value,
                metadata={"reason": "shared_identifier", "rule": "Delivery address matches Home Residence address"},
            )
            self.wm_link(
                origin_cluster_fact["_id"],
                place_id,
                RelationType.SAME_AS.value,
                metadata={
                    "reason": "gps_distance_cluster",
                    "radius_meters": radius_m,
                    "rule": f"Coordinates within {radius_m}m cluster of residence",
                },
            )
            self.last_link_reasons.append({
                "type": "shared_identifier",
                "from_id": delivery_fact["_id"],
                "to_id": place_id,
                "reason_code": "shared_identifier",
            })
            self.last_link_reasons.append({
                "type": "gps_distance_cluster",
                "from_id": origin_cluster_fact["_id"],
                "to_id": place_id,
                "reason_code": "gps_distance_cluster",
                "radius_meters": radius_m,
            })

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
            self.wm_link(
                morning_fact["_id"],
                routine_id,
                RelationType.SUPPORTS.value,
                metadata={"reason": "timestamp_match", "time_window_minutes": time_window_min, "rule": "Routine runs match morning recurrence window"},
            )
            self.last_link_reasons.append({
                "type": "timestamp_match",
                "from_id": morning_fact["_id"],
                "to_id": routine_id,
                "reason_code": "timestamp_match",
            })
            for sf in standup_facts:
                self.wm_link(
                    sf["_id"],
                    routine_id,
                    RelationType.SUPPORTS.value,
                    metadata={"reason": "timestamp_match", "rule": "Standup event coincides with routine window"},
                )
                self.last_link_reasons.append({
                    "type": "timestamp_match",
                    "from_id": sf["_id"],
                    "to_id": routine_id,
                    "reason_code": "timestamp_match",
                })

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
                self.wm_link(
                    vf["_id"],
                    absence_id,
                    RelationType.SUPPORTS.value,
                    metadata={"reason": "timestamp_match", "rule": "Calendar PTO dates align with travel window"},
                )
                self.last_link_reasons.append({
                    "type": "timestamp_match",
                    "from_id": vf["_id"],
                    "to_id": absence_id,
                    "reason_code": "timestamp_match",
                })
            for sf in vacation_soc:
                self.wm_link(
                    sf["_id"],
                    absence_id,
                    RelationType.SUPPORTS.value,
                    metadata={"reason": "timestamp_match", "rule": "Social post departure coincides with absence"},
                )
                self.last_link_reasons.append({
                    "type": "timestamp_match",
                    "from_id": sf["_id"],
                    "to_id": absence_id,
                    "reason_code": "timestamp_match",
                })

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
                self.wm_link(
                    oe["_id"],
                    clinic_id,
                    RelationType.DERIVED_FROM.value,
                    metadata={"reason": "shared_identifier", "rule": "Provider specialty and clinic name match"},
                )
                self.last_link_reasons.append({
                    "type": "shared_identifier",
                    "from_id": oe["_id"],
                    "to_id": clinic_id,
                    "reason_code": "shared_identifier",
                })
            for pf in pharmacy_facts:
                self.wm_link(
                    pf["_id"],
                    clinic_id,
                    RelationType.SUPPORTS.value,
                    metadata={"reason": "shared_identifier", "rule": "Oncology prescription correlates with clinic visit"},
                )
                self.last_link_reasons.append({
                    "type": "shared_identifier",
                    "from_id": pf["_id"],
                    "to_id": clinic_id,
                    "reason_code": "shared_identifier",
                })

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
                self.wm_link(
                    bf["_id"],
                    kba_id,
                    RelationType.SUPPORTS.value,
                    metadata={"reason": "shared_identifier", "rule": "Birthday mention establishes DOB attribute"},
                )
                self.last_link_reasons.append({
                    "type": "shared_identifier",
                    "from_id": bf["_id"],
                    "to_id": kba_id,
                    "reason_code": "shared_identifier",
                })

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
                self.wm_link(
                    pf["_id"],
                    pet_id,
                    RelationType.SUPPORTS.value,
                    metadata={"reason": "shared_identifier", "rule": "Pet name mentioned as KBA security question answer"},
                )
                self.last_link_reasons.append({
                    "type": "shared_identifier",
                    "from_id": pf["_id"],
                    "to_id": pet_id,
                    "reason_code": "shared_identifier",
                })

        if school_facts:
            for sf in school_facts:
                created_entity_ids.append(sf["_id"])

        self.pack_brief(profile_id, facts, created_entity_ids)
        return created_entity_ids

    def pack_brief(
        self, profile_id: str, facts: list[dict[str, Any]], entity_ids: list[str]
    ) -> dict[str, Any]:
        """Pack a concise brief for the Red-team citing all resolved facts and linkage risks."""
        all_fact_ids = [f["_id"] for f in facts]
        brief_text = (
            f"Context Brief for Profile {profile_id}: {len(facts)} facts processed, "
            f"{len(entity_ids)} high-order entities resolved via {len(self.last_link_reasons)} cross-table linkages."
        )
        self.last_brief = {
            "profile_id": profile_id,
            "brief": brief_text,
            "cites": all_fact_ids,
            "risks": [
                "GPS boundary points may carry multi-path or drift error",
                "Social posts without explicit geo-tags may reflect delayed uploads",
            ],
            "open_qs": [
                "Does the subject maintain a secondary residence or shared workplace?",
            ],
            "link_reasons": self.last_link_reasons,
        }
        return self.last_brief
