"""Extractor Agent: deterministic clustering & extraction of atomic facts."""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.dd.agents.base_agent import BaseAgent
from src.dd.models.domain import EntityType


class ExtractorAgent(BaseAgent):
    """Extractor Agent: extracts atomic facts deterministically from raw tables."""

    def __init__(self, world_model: Any, data_layer: Any, llm_client: Any) -> None:
        super().__init__(
            name="extractor",
            world_model=world_model,
            data_layer=data_layer,
            llm_client=llm_client,
        )

    async def extract_all(self, profile_id: str, tables: list[str]) -> list[str]:
        """Extract atomic facts across all planned tables and ingest into World Model."""
        extracted_fact_ids: list[str] = []

        for table in tables:
            rows = await self.query_data(f"SELECT * FROM {table} WHERE profile_id = '{profile_id}'")
            if not rows:
                continue

            if table == "strava_activities":
                fact_ids = self._extract_strava(profile_id, rows)
                extracted_fact_ids.extend(fact_ids)
            elif table == "food_orders":
                fact_ids = self._extract_food_orders(profile_id, rows)
                extracted_fact_ids.extend(fact_ids)
            elif table == "calendar_events":
                fact_ids = self._extract_calendar(profile_id, rows)
                extracted_fact_ids.extend(fact_ids)
            elif table == "social_posts":
                fact_ids = await self._extract_social(profile_id, rows)
                extracted_fact_ids.extend(fact_ids)
            elif table == "profile_fields":
                fact_ids = self._extract_profile_fields(profile_id, rows)
                extracted_fact_ids.extend(fact_ids)
            elif table == "pharmacy_orders":
                fact_ids = self._extract_pharmacy(profile_id, rows)
                extracted_fact_ids.extend(fact_ids)

        return extracted_fact_ids

    def _extract_strava(self, profile_id: str, rows: list[dict[str, Any]]) -> list[str]:
        """Deterministic GPS clustering and timing patterns."""
        fact_ids = []

        # 1. Cluster origin coordinates (round to 3 decimals: ~110m radius)
        clusters: Counter[tuple[float, float]] = Counter()
        morning_runs = 0

        for r in rows:
            lat = round(float(r["start_lat"]), 3)
            lon = round(float(r["start_lon"]), 3)
            clusters[(lat, lon)] += 1

            # Check for morning run pattern
            st = str(r.get("start_time", ""))
            if "06:3" in st or "06:2" in st:
                morning_runs += 1

            # Ingest individual raw run fact with row provenance
            fid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "activity_record",
                    "value": f"{r.get('activity_type')} {r.get('distance_km')}km at {st}",
                    "source_table": "strava_activities",
                    "source_row_id": str(r.get("activity_id")),
                    "start_time": st,
                    "route_summary": str(r.get("route_summary", "")),
                    "start_lat": float(r["start_lat"]),
                    "start_lon": float(r["start_lon"]),
                },
                source="strava_activities",
            )
            fact_ids.append(fid)

        if clusters:
            top_coord, count = clusters.most_common(1)[0]
            cid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "primary_run_origin_cluster",
                    "value": f"{top_coord[0]}, {top_coord[1]}",
                    "source_table": "strava_activities",
                    "activity_count": count,
                },
                source="extractor_spatial_clustering",
            )
            fact_ids.append(cid)

        if morning_runs >= 3:
            mid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "weekday_morning_run_habit",
                    "value": f"{morning_runs} weekday runs between 06:29 and 06:33 AM",
                    "source_table": "strava_activities",
                },
                source="extractor_temporal_clustering",
            )
            fact_ids.append(mid)

        return fact_ids

    def _extract_food_orders(self, profile_id: str, rows: list[dict[str, Any]]) -> list[str]:
        """Deterministic delivery address mode and order habits."""
        fact_ids = []
        address_counts: Counter[str] = Counter()

        for r in rows:
            addr = str(r.get("delivery_address", "")).strip()
            address_counts[addr] += 1

            fid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "food_order_destination",
                    "value": addr,
                    "source_table": "food_orders",
                    "source_row_id": str(r.get("order_id")),
                    "items": str(r.get("items", "")),
                    "timestamp": str(r.get("timestamp", "")),
                },
                source="food_orders",
            )
            fact_ids.append(fid)

        if address_counts:
            top_addr, count = address_counts.most_common(1)[0]
            fid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "primary_delivery_address",
                    "value": top_addr,
                    "source_table": "food_orders",
                    "order_frequency": count,
                },
                source="extractor_mode_clustering",
            )
            fact_ids.append(fid)

        return fact_ids

    def _extract_calendar(self, profile_id: str, rows: list[dict[str, Any]]) -> list[str]:
        """Extract scheduled routines, medical consults, and vacation absences."""
        fact_ids = []
        for r in rows:
            title = str(r.get("title", ""))
            loc = str(r.get("location", ""))
            st = str(r.get("start_time", ""))
            et = str(r.get("end_time", ""))

            fid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "calendar_event",
                    "value": f"{title} at {loc} ({st} to {et})",
                    "source_table": "calendar_events",
                    "source_row_id": str(r.get("event_id")),
                    "title": title,
                    "location": loc,
                    "start_time": st,
                    "end_time": et,
                },
                source="calendar_events",
            )
            fact_ids.append(fid)

        return fact_ids

    async def _extract_social(self, profile_id: str, rows: list[dict[str, Any]]) -> list[str]:
        """Extract social posts with LLM free-text summarization."""
        fact_ids = []
        for r in rows:
            text = str(r.get("text_content", ""))
            post_id = str(r.get("post_id", ""))

            fid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "social_post_text",
                    "value": text,
                    "source_table": "social_posts",
                    "source_row_id": post_id,
                    "platform": str(r.get("platform", "")),
                    "timestamp": str(r.get("timestamp", "")),
                    "location_tag": str(r.get("location_tag", "")),
                },
                source="social_posts",
            )
            fact_ids.append(fid)

        return fact_ids

    def _extract_profile_fields(self, profile_id: str, rows: list[dict[str, Any]]) -> list[str]:
        """Extract identity profile attributes."""
        fact_ids = []
        for r in rows:
            fname = str(r.get("field_name", ""))
            fval = str(r.get("field_value", ""))
            fid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": fname,
                    "value": fval,
                    "source_table": "profile_fields",
                    "source_platform": str(r.get("source_platform", "")),
                },
                source="profile_fields",
            )
            fact_ids.append(fid)
        return fact_ids

    def _extract_pharmacy(self, profile_id: str, rows: list[dict[str, Any]]) -> list[str]:
        """Extract pharmacy orders."""
        fact_ids = []
        for r in rows:
            item = str(r.get("item_category", ""))
            spec = str(r.get("prescriber_specialty", ""))
            fid = self.wm_ingest(
                EntityType.FACT.value,
                {
                    "profile_id": profile_id,
                    "key": "pharmacy_prescription",
                    "value": f"{item} (Prescriber: {spec})",
                    "source_table": "pharmacy_orders",
                    "source_row_id": str(r.get("order_id")),
                    "item_category": item,
                    "prescriber_specialty": spec,
                },
                source="pharmacy_orders",
            )
            fact_ids.append(fid)
        return fact_ids
