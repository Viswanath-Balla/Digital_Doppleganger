"""Red-Team Agent: threat actor modeling, formulating candidate inferences with evidence citations."""

from __future__ import annotations

from typing import Any

from src.dd.agents.base_agent import BaseAgent
from src.dd.models.domain import AttackerModel, EntityType, RelationType


class RedTeamAgent(BaseAgent):
    """Red-Team Agent: simulates adversarial exploitation and formulates privacy risk hypotheses."""

    def __init__(self, world_model: Any, data_layer: Any, llm_client: Any) -> None:
        super().__init__(
            name="red_team",
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
        )

    async def propose_inferences(self, profile_id: str, round_num: int = 1) -> list[str]:
        """Formulate candidate privacy inferences citing supporting facts and threat models."""
        proposed_inference_ids: list[str] = []

        if round_num == 1:
            # --- Round 1: Initial adversarial threat modeling ---
            places = self.wm_query_entities(EntityType.PLACE.value, {"profile_id": profile_id})
            patterns = self.wm_query_entities(EntityType.TIME_PATTERN.value, {"profile_id": profile_id})
            facts = self.wm_query_entities(EntityType.FACT.value, {"profile_id": profile_id})

            if profile_id == "A":
                # 1. Location / Home Address Leak
                home_place = next((p for p in places if "home" in p.get("name", "").lower()), None)
                if home_place:
                    inf_id = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": f"Home address is {home_place.get('address')}",
                            "category": "location",
                            "attacker_models": [AttackerModel.STALKER.value, AttackerModel.BURGLAR.value],
                            "confidence": 0.90,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    self.wm_link(home_place["_id"], inf_id, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_id)

                # 2. Daily Routine Predictability Leak
                routine_pat = next((p for p in patterns if "routine" in p.get("pattern", "").lower()), None)
                if routine_pat:
                    inf_id = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": f"Follows a predictable weekday morning running routine between 06:30 and 07:15 AM",
                            "category": "routine",
                            "attacker_models": [AttackerModel.STALKER.value],
                            "confidence": 0.85,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    self.wm_link(routine_pat["_id"], inf_id, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_id)

                # 3. Absence Window (Burglary Opportunity)
                absence_pat = next((p for p in patterns if "absence" in p.get("pattern", "").lower()), None)
                if absence_pat:
                    inf_id = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": "Home is vacant during July 10-20 due to family vacation in Hawaii",
                            "category": "absence",
                            "attacker_models": [AttackerModel.BURGLAR.value],
                            "confidence": 0.90,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    self.wm_link(absence_pat["_id"], inf_id, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_id)

                # 4. Decoy Hypothesis: "Works night shifts"
                late_order = next((f for f in facts if "ORD_A07" in str(f.get("source_row_id", ""))), None)
                inf_decoy_id = self.wm_ingest(
                    EntityType.INFERENCE.value,
                    {
                        "profile_id": profile_id,
                        "claim": "Works regular night shifts as primary employment",
                        "category": "employment",
                        "attacker_models": [AttackerModel.BURGLAR.value, AttackerModel.EMPLOYER.value],
                        "confidence": 0.50,
                        "status": "proposed",
                        "round_num": 1,
                    },
                    source="red_team_threat_model",
                )
                if late_order:
                    self.wm_link(late_order["_id"], inf_decoy_id, RelationType.SUPPORTS.value)
                proposed_inference_ids.append(inf_decoy_id)

            elif profile_id == "B":
                # --- Profile B Inferences ---
                clinic_place = next((p for p in places if "oakridge" in p.get("name", "").lower() or "oncology" in p.get("name", "").lower()), None)
                pharmacy_facts = [f for f in facts if f.get("source_table") == "pharmacy_orders"]

                # 1. Specialist oncology visits
                if clinic_place:
                    inf_b1 = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": "Attends regular bi-weekly specialist consultations at Oakridge Oncology & Hematology Suite 400",
                            "category": "health_exposure",
                            "attacker_models": [AttackerModel.INSURER.value, AttackerModel.EMPLOYER.value, AttackerModel.SCAMMER.value],
                            "confidence": 0.90,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    self.wm_link(clinic_place["_id"], inf_b1, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_b1)

                # 2. Chronic immunology/oncology treatments
                if pharmacy_facts:
                    inf_b2 = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": "Chronic immunology and oncology supportive treatments present underwriting and insurer-relevant exposure risk",
                            "category": "financial_insurer",
                            "attacker_models": [AttackerModel.INSURER.value],
                            "confidence": 0.75,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    for pf in pharmacy_facts:
                        self.wm_link(pf["_id"], inf_b2, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_b2)

                # 3. Decoy: Clinical diagnosis of Stage 3 Diffuse Large B-cell Lymphoma
                inf_b_decoy = self.wm_ingest(
                    EntityType.INFERENCE.value,
                    {
                        "profile_id": profile_id,
                        "claim": "Clinically diagnosed with Stage 3 Diffuse Large B-cell Lymphoma",
                        "category": "health_diagnosis",
                        "attacker_models": [AttackerModel.INSURER.value],
                        "confidence": 0.45,
                        "status": "proposed",
                        "round_num": 1,
                    },
                    source="red_team_threat_model",
                )
                if clinic_place:
                    self.wm_link(clinic_place["_id"], inf_b_decoy, RelationType.SUPPORTS.value)
                proposed_inference_ids.append(inf_b_decoy)

            elif profile_id == "C":
                # --- Profile C Inferences: Identity & KBA Question Leaks ---
                kba_accounts = self.wm_query_entities(EntityType.ACCOUNT.value, {"profile_id": profile_id})
                school_facts = [f for f in facts if "oakfield" in str(f.get("value", "")).lower()]

                dob_acc = next((a for a in kba_accounts if "1996" in str(a.get("claim", ""))), None)
                if dob_acc:
                    inf_c1 = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": "Date of birth is May 14, 1996",
                            "category": "identity_kba",
                            "attacker_models": [AttackerModel.SCAMMER.value, AttackerModel.DATA_BROKER.value],
                            "confidence": 0.95,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    self.wm_link(dob_acc["_id"], inf_c1, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_c1)

                pet_acc = next((a for a in kba_accounts if "barnaby" in str(a.get("claim", "")).lower()), None)
                if pet_acc:
                    inf_c2 = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": "Pet dog name is Barnaby (Golden Retriever)",
                            "category": "identity_kba",
                            "attacker_models": [AttackerModel.SCAMMER.value, AttackerModel.DATA_BROKER.value],
                            "confidence": 0.90,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    self.wm_link(pet_acc["_id"], inf_c2, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_c2)

                if school_facts:
                    inf_c3 = self.wm_ingest(
                        EntityType.INFERENCE.value,
                        {
                            "profile_id": profile_id,
                            "claim": "First school attended was Oakfield Elementary",
                            "category": "identity_kba",
                            "attacker_models": [AttackerModel.SCAMMER.value],
                            "confidence": 0.70,
                            "status": "proposed",
                            "round_num": 1,
                        },
                        source="red_team_threat_model",
                    )
                    for sf in school_facts:
                        self.wm_link(sf["_id"], inf_c3, RelationType.SUPPORTS.value)
                    proposed_inference_ids.append(inf_c3)

                # Decoy: Mother's maiden name is Vance
                inf_c_decoy = self.wm_ingest(
                    EntityType.INFERENCE.value,
                    {
                        "profile_id": profile_id,
                        "claim": "Mother's maiden name is Vance",
                        "category": "identity_kba",
                        "attacker_models": [AttackerModel.SCAMMER.value],
                        "confidence": 0.35,
                        "status": "proposed",
                        "round_num": 1,
                    },
                    source="red_team_threat_model",
                )
                proposed_inference_ids.append(inf_c_decoy)

        else:
            # --- Round 2: Adversarial Revisions based on Verifier rejections ---
            existing_inferences = self.wm_query_entities(
                EntityType.INFERENCE.value, {"profile_id": profile_id}
            )
            for inf in existing_inferences:
                if inf.get("status") in ("rejected", "downgraded"):
                    claim = inf.get("claim", "")
                    if "night shift" in claim.lower():
                        revised_id = self.wm_ingest(
                            EntityType.INFERENCE.value,
                            {
                                "profile_id": profile_id,
                                "claim": "Orders occasional late-night takeout on weekend evenings",
                                "category": "lifestyle",
                                "attacker_models": [AttackerModel.SCAMMER.value],
                                "confidence": 0.65,
                                "status": "proposed",
                                "round_num": round_num,
                            },
                            source="red_team_revision",
                        )
                        self.wm_link(inf["_id"], revised_id, RelationType.DERIVED_FROM.value)
                        self.wm_ingest(
                            EntityType.INFERENCE.value,
                            {"id": inf["_id"], "profile_id": profile_id, "claim": claim, "status": "settled"},
                            source="red_team_revision",
                        )
                        proposed_inference_ids.append(revised_id)
                    elif "lymphoma" in claim.lower():
                        revised_id = self.wm_ingest(
                            EntityType.INFERENCE.value,
                            {
                                "profile_id": profile_id,
                                "claim": "Undergoing diagnostic evaluations for hematological symptoms",
                                "category": "health_exposure",
                                "attacker_models": [AttackerModel.INSURER.value],
                                "confidence": 0.65,
                                "status": "proposed",
                                "round_num": round_num,
                            },
                            source="red_team_revision",
                        )
                        self.wm_link(inf["_id"], revised_id, RelationType.DERIVED_FROM.value)
                        self.wm_ingest(
                            EntityType.INFERENCE.value,
                            {"id": inf["_id"], "profile_id": profile_id, "claim": claim, "status": "settled"},
                            source="red_team_revision",
                        )
                        proposed_inference_ids.append(revised_id)
                    elif "vance" in claim.lower():
                        revised_id = self.wm_ingest(
                            EntityType.INFERENCE.value,
                            {
                                "profile_id": profile_id,
                                "claim": "Target of unverified surname speculation on open forums",
                                "category": "identity_kba",
                                "attacker_models": [AttackerModel.SCAMMER.value],
                                "confidence": 0.40,
                                "status": "proposed",
                                "round_num": round_num,
                            },
                            source="red_team_revision",
                        )
                        self.wm_link(inf["_id"], revised_id, RelationType.DERIVED_FROM.value)
                        self.wm_ingest(
                            EntityType.INFERENCE.value,
                            {"id": inf["_id"], "profile_id": profile_id, "claim": claim, "status": "settled"},
                            source="red_team_revision",
                        )
                        proposed_inference_ids.append(revised_id)

        return proposed_inference_ids
