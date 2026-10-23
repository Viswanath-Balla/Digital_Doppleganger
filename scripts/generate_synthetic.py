"""Synthetic data and ground-truth generator for Digital Doppelgänger.

Deterministically creates 6 CSV tables under data/sample/ for Profiles A, B, and C:
  - profile_fields.csv
  - strava_activities.csv
  - food_orders.csv
  - calendar_events.csv
  - social_posts.csv
  - pharmacy_orders.csv

Also writes data/ground_truth.json containing planted privacy leaks and decoys.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT_DIR / "data" / "sample"
GROUND_TRUTH_FILE = ROOT_DIR / "data" / "ground_truth.json"


def generate_all() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. profile_fields
    # -------------------------------------------------------------------------
    profile_fields = [
        # Profile A - Alex Rivera
        {"profile_id": "A", "field_name": "full_name", "field_value": "Alex Rivera", "source_platform": "linkedin", "updated_at": "2026-01-15T09:00:00Z"},
        {"profile_id": "A", "field_name": "email", "field_value": "alex.rivera.dev@gmail.com", "source_platform": "google", "updated_at": "2026-01-10T08:30:00Z"},
        {"profile_id": "A", "field_name": "phone", "field_value": "+1-555-0142", "source_platform": "uber_eats", "updated_at": "2026-02-01T12:00:00Z"},
        {"profile_id": "A", "field_name": "employer", "field_value": "Nexora Systems", "source_platform": "linkedin", "updated_at": "2026-01-15T09:00:00Z"},
        {"profile_id": "A", "field_name": "job_title", "field_value": "Senior Backend Engineer", "source_platform": "linkedin", "updated_at": "2026-01-15T09:00:00Z"},
        {"profile_id": "A", "field_name": "city", "field_value": "Springfield", "source_platform": "strava", "updated_at": "2026-03-01T07:00:00Z"},

        # Profile B - Brenda Vance
        {"profile_id": "B", "field_name": "full_name", "field_value": "Brenda Vance", "source_platform": "linkedin", "updated_at": "2026-01-12T10:00:00Z"},
        {"profile_id": "B", "field_name": "email", "field_value": "b.vance.design@outlook.com", "source_platform": "outlook", "updated_at": "2026-01-05T11:00:00Z"},
        {"profile_id": "B", "field_name": "employer", "field_value": "Aura Studio", "source_platform": "linkedin", "updated_at": "2026-01-12T10:00:00Z"},
        {"profile_id": "B", "field_name": "job_title", "field_value": "Product Design Lead", "source_platform": "linkedin", "updated_at": "2026-01-12T10:00:00Z"},
        {"profile_id": "B", "field_name": "emergency_contact", "field_value": "David Vance (Brother)", "source_platform": "health_portal", "updated_at": "2026-02-14T14:30:00Z"},

        # Profile C - Charlie Chen
        {"profile_id": "C", "field_name": "full_name", "field_value": "Charlie Chen", "source_platform": "instagram", "updated_at": "2026-01-20T16:00:00Z"},
        {"profile_id": "C", "field_name": "handle", "field_value": "@charlie_runs_fast", "source_platform": "instagram", "updated_at": "2026-01-20T16:00:00Z"},
        {"profile_id": "C", "field_name": "email", "field_value": "charlie.chen96@yahoo.com", "source_platform": "yahoo", "updated_at": "2026-01-01T10:00:00Z"},
        {"profile_id": "C", "field_name": "birth_year", "field_value": "1996", "source_platform": "forum", "updated_at": "2026-02-10T19:00:00Z"},
        {"profile_id": "C", "field_name": "hometown", "field_value": "Oakfield", "source_platform": "facebook", "updated_at": "2026-01-02T12:00:00Z"},
    ]

    _write_csv("profile_fields.csv", [
        "profile_id", "field_name", "field_value", "source_platform", "updated_at"
    ], profile_fields)

    # -------------------------------------------------------------------------
    # 2. strava_activities
    # -------------------------------------------------------------------------
    strava_activities = [
        # Profile A: Regular morning runs starting from home coordinates (39.7817, -89.6501)
        {"profile_id": "A", "activity_id": "STR_A01", "activity_type": "Run", "start_time": "2026-06-01T06:30:00Z", "end_time": "2026-06-01T07:15:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 6.2, "route_summary": "Morning loop via Elm Park"},
        {"profile_id": "A", "activity_id": "STR_A02", "activity_type": "Run", "start_time": "2026-06-02T06:32:00Z", "end_time": "2026-06-02T07:16:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 6.1, "route_summary": "Morning loop via Elm Park"},
        {"profile_id": "A", "activity_id": "STR_A03", "activity_type": "Run", "start_time": "2026-06-03T06:29:00Z", "end_time": "2026-06-03T07:14:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 6.3, "route_summary": "Morning loop via Elm Park"},
        {"profile_id": "A", "activity_id": "STR_A04", "activity_type": "Run", "start_time": "2026-06-04T06:31:00Z", "end_time": "2026-06-04T07:17:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 6.2, "route_summary": "Morning loop via Elm Park"},
        {"profile_id": "A", "activity_id": "STR_A05", "activity_type": "Run", "start_time": "2026-06-05T06:30:00Z", "end_time": "2026-06-05T07:15:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 6.0, "route_summary": "Morning loop via Elm Park"},
        {"profile_id": "A", "activity_id": "STR_A06", "activity_type": "Ride", "start_time": "2026-06-06T09:00:00Z", "end_time": "2026-06-06T10:30:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 24.5, "route_summary": "Weekend perimeter ride"},
        {"profile_id": "A", "activity_id": "STR_A07", "activity_type": "Run", "start_time": "2026-06-08T06:30:00Z", "end_time": "2026-06-08T07:15:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 6.2, "route_summary": "Morning loop via Elm Park"},
        {"profile_id": "A", "activity_id": "STR_A08", "activity_type": "Run", "start_time": "2026-06-09T06:33:00Z", "end_time": "2026-06-09T07:18:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 6.1, "route_summary": "Morning loop via Elm Park"},
        # Note: No runs between 2026-07-10 and 2026-07-20 (absence window)
        {"profile_id": "A", "activity_id": "STR_A09", "activity_type": "Run", "start_time": "2026-07-22T06:30:00Z", "end_time": "2026-07-22T07:15:00Z", "start_lat": 39.7817, "start_lon": -89.6501, "distance_km": 5.8, "route_summary": "Post-vacation recovery jog"},

        # Profile B: Occasional gentle walks around Oakridge Park
        {"profile_id": "B", "activity_id": "STR_B01", "activity_type": "Walk", "start_time": "2026-05-10T11:00:00Z", "end_time": "2026-05-10T11:45:00Z", "start_lat": 42.3314, "start_lon": -83.0458, "distance_km": 2.1, "route_summary": "Oakridge Park trail walk"},
        {"profile_id": "B", "activity_id": "STR_B02", "activity_type": "Walk", "start_time": "2026-05-24T10:30:00Z", "end_time": "2026-05-24T11:15:00Z", "start_lat": 42.3314, "start_lon": -83.0458, "distance_km": 2.0, "route_summary": "Oakridge Park trail walk"},
        {"profile_id": "B", "activity_id": "STR_B03", "activity_type": "Walk", "start_time": "2026-06-07T10:45:00Z", "end_time": "2026-06-07T11:30:00Z", "start_lat": 42.3314, "start_lon": -83.0458, "distance_km": 1.9, "route_summary": "Oakridge Park trail walk"},

        # Profile C: Moderate weekend 5k runner
        {"profile_id": "C", "activity_id": "STR_C01", "activity_type": "Run", "start_time": "2026-04-12T08:00:00Z", "end_time": "2026-04-12T08:32:00Z", "start_lat": 37.7749, "start_lon": -122.4194, "distance_km": 5.1, "route_summary": "Marina waterfront loop"},
        {"profile_id": "C", "activity_id": "STR_C02", "activity_type": "Run", "start_time": "2026-04-19T08:15:00Z", "end_time": "2026-04-19T08:48:00Z", "start_lat": 37.7749, "start_lon": -122.4194, "distance_km": 5.0, "route_summary": "Marina waterfront loop"},
    ]

    _write_csv("strava_activities.csv", [
        "profile_id", "activity_id", "activity_type", "start_time", "end_time", "start_lat", "start_lon", "distance_km", "route_summary"
    ], strava_activities)

    # -------------------------------------------------------------------------
    # 3. food_orders
    # -------------------------------------------------------------------------
    food_orders = [
        # Profile A: Frequent deliveries to home address 742 Evergreen Terr, Springfield
        {"profile_id": "A", "order_id": "ORD_A01", "timestamp": "2026-06-01T19:15:00Z", "delivery_address": "742 Evergreen Terr, Springfield", "items": "Pad Thai, Spring Rolls", "restaurant_name": "Siam Garden", "total_amount": 28.50},
        {"profile_id": "A", "order_id": "ORD_A02", "timestamp": "2026-06-04T19:30:00Z", "delivery_address": "742 Evergreen Terr, Springfield", "items": "Margherita Pizza, Diet Coke", "restaurant_name": "Luigi's Wood Fired", "total_amount": 22.00},
        {"profile_id": "A", "order_id": "ORD_A03", "timestamp": "2026-06-09T18:45:00Z", "delivery_address": "742 Evergreen Terr, Springfield", "items": "Salmon Poke Bowl", "restaurant_name": "Aloha Poke", "total_amount": 19.75},
        {"profile_id": "A", "order_id": "ORD_A04", "timestamp": "2026-06-12T20:00:00Z", "delivery_address": "742 Evergreen Terr, Springfield", "items": "Veggie Burrito, Guacamole", "restaurant_name": "Cantina Mexicana", "total_amount": 17.50},
        {"profile_id": "A", "order_id": "ORD_A05", "timestamp": "2026-06-16T19:20:00Z", "delivery_address": "742 Evergreen Terr, Springfield", "items": "Chicken Tikka Masala, Garlic Naan", "restaurant_name": "Taj Flavors", "total_amount": 31.00},
        # Profile A work delivery
        {"profile_id": "A", "order_id": "ORD_A06", "timestamp": "2026-06-05T12:15:00Z", "delivery_address": "Nexora Systems, 100 Innovation Way, Springfield", "items": "Club Sandwich, Iced Tea", "restaurant_name": "Corner Deli", "total_amount": 14.25},
        # Profile A decoy: solitary late-night order on a weekend
        {"profile_id": "A", "order_id": "ORD_A07", "timestamp": "2026-06-13T23:45:00Z", "delivery_address": "742 Evergreen Terr, Springfield", "items": "Late Night Cheeseburger, Fries", "restaurant_name": "Midnight Diner", "total_amount": 16.80},

        # Profile B
        {"profile_id": "B", "order_id": "ORD_B01", "timestamp": "2026-05-15T18:30:00Z", "delivery_address": "404 Meadow Lane, Detroit", "items": "Organic Green Salad, Lentil Soup", "restaurant_name": "Pure Harvest", "total_amount": 24.00},
        {"profile_id": "B", "order_id": "ORD_B02", "timestamp": "2026-05-29T18:40:00Z", "delivery_address": "404 Meadow Lane, Detroit", "items": "Steamed Dumplings, Ginger Broth", "restaurant_name": "Lotus Garden", "total_amount": 21.50},

        # Profile C
        {"profile_id": "C", "order_id": "ORD_C01", "timestamp": "2026-04-10T19:00:00Z", "delivery_address": "88 Clipper St, San Francisco", "items": "Spicy Ramen, Gyoza", "restaurant_name": "Ramen Hiro", "total_amount": 26.00},
        {"profile_id": "C", "order_id": "ORD_C02", "timestamp": "2026-04-18T19:30:00Z", "delivery_address": "88 Clipper St, San Francisco", "items": "Chicken Katsu Curry", "restaurant_name": "Tokyo Express", "total_amount": 20.00},
    ]

    _write_csv("food_orders.csv", [
        "profile_id", "order_id", "timestamp", "delivery_address", "items", "restaurant_name", "total_amount"
    ], food_orders)

    # -------------------------------------------------------------------------
    # 4. calendar_events
    # -------------------------------------------------------------------------
    calendar_events = [
        # Profile A: Workday standup & clear absence window Jul 10 - Jul 20
        {"profile_id": "A", "event_id": "CAL_A01", "title": "Engineering Standup", "start_time": "2026-06-01T09:30:00Z", "end_time": "2026-06-01T10:00:00Z", "location": "Google Meet", "description": "Daily backend sync"},
        {"profile_id": "A", "event_id": "CAL_A02", "title": "Engineering Standup", "start_time": "2026-06-02T09:30:00Z", "end_time": "2026-06-02T10:00:00Z", "location": "Google Meet", "description": "Daily backend sync"},
        {"profile_id": "A", "event_id": "CAL_A03", "title": "1:1 with Tech Lead", "start_time": "2026-06-03T14:00:00Z", "end_time": "2026-06-03T14:30:00Z", "location": "Conf Room 3B", "description": "Quarterly performance checkin"},
        {"profile_id": "A", "event_id": "CAL_A04", "title": "PTO - Annual Hawaii Vacation", "start_time": "2026-07-10T00:00:00Z", "end_time": "2026-07-20T23:59:59Z", "location": "Honolulu, HI", "description": "Family summer vacation, house locked"},
        {"profile_id": "A", "event_id": "CAL_A05", "title": "Flight: SFO to HNL", "start_time": "2026-07-10T08:15:00Z", "end_time": "2026-07-10T13:45:00Z", "location": "United Airlines UA 238", "description": "Outbound departure"},

        # Profile B: Bi-weekly recurring specialist visits
        {"profile_id": "B", "event_id": "CAL_B01", "title": "Specialist Consultation", "start_time": "2026-05-05T14:00:00Z", "end_time": "2026-05-05T15:30:00Z", "location": "Oakridge Oncology & Hematology Suite 400", "description": "Followup panel and lab review with Dr. K. Mehta"},
        {"profile_id": "B", "event_id": "CAL_B02", "title": "Infusion Therapy Session", "start_time": "2026-05-19T13:00:00Z", "end_time": "2026-05-19T16:00:00Z", "location": "Oakridge Oncology & Hematology Suite 400", "description": "Bi-weekly scheduled maintenance infusion"},
        {"profile_id": "B", "event_id": "CAL_B03", "title": "Followup Consultation", "start_time": "2026-06-02T14:00:00Z", "end_time": "2026-06-02T15:30:00Z", "location": "Oakridge Oncology & Hematology Suite 400", "description": "Lab results and progress assessment"},
        {"profile_id": "B", "event_id": "CAL_B04", "title": "Design Sprint Review", "start_time": "2026-06-10T10:00:00Z", "end_time": "2026-06-10T11:30:00Z", "location": "Aura Studio Room A", "description": "Q3 mobile redesign mockup walk"},

        # Profile C: Birthday reminder
        {"profile_id": "C", "event_id": "CAL_C01", "title": "My 30th Birthday Dinner!", "start_time": "2026-05-14T19:00:00Z", "end_time": "2026-05-14T22:00:00Z", "location": "Bistro Central, San Francisco", "description": "Celebrating with close friends and family"},
        {"profile_id": "C", "event_id": "CAL_C02", "title": "Barnaby Vet Annual Checkup", "start_time": "2026-05-20T11:00:00Z", "end_time": "2026-05-20T12:00:00Z", "location": "Bay Animal Hospital", "description": "Rabies vaccine booster for Barnaby"},
    ]

    _write_csv("calendar_events.csv", [
        "profile_id", "event_id", "title", "start_time", "end_time", "location", "description"
    ], calendar_events)

    # -------------------------------------------------------------------------
    # 5. social_posts
    # -------------------------------------------------------------------------
    social_posts = [
        # Profile A: Vacation departure leak
        {"profile_id": "A", "post_id": "SOC_A01", "timestamp": "2026-07-10T07:00:00Z", "platform": "twitter", "text_content": "Bag packed, lights off, and airport bound for the next 10 days! Hawaii here we come 🌺✈️", "location_tag": "SFO International Airport", "media_type": "photo"},
        {"profile_id": "A", "post_id": "SOC_A02", "timestamp": "2026-07-15T18:00:00Z", "platform": "instagram", "text_content": "Sunset over Waikiki beach. Unplugged and peaceful.", "location_tag": "Honolulu, Hawaii", "media_type": "photo"},
        {"profile_id": "A", "post_id": "SOC_A03", "timestamp": "2026-06-03T07:25:00Z", "platform": "twitter", "text_content": "Beautiful crisp 62F morning for a run around the neighborhood. Coffee time!", "location_tag": "Springfield", "media_type": "text"},

        # Profile B: Subtle references to rest and health routine
        {"profile_id": "B", "post_id": "SOC_B01", "timestamp": "2026-05-19T17:30:00Z", "platform": "threads", "text_content": "Tough afternoon at the medical center, but feeling grateful for my care team. Taking the evening to rest.", "location_tag": "Detroit, MI", "media_type": "text"},
        {"profile_id": "B", "post_id": "SOC_B02", "timestamp": "2026-06-05T14:00:00Z", "platform": "instagram", "text_content": "New ceramic collection design exploration. Slow steady progress.", "location_tag": "Detroit, MI", "media_type": "photo"},

        # Profile C: Birthday, pet name, and alumni event
        {"profile_id": "C", "post_id": "SOC_C01", "timestamp": "2026-05-14T10:00:00Z", "platform": "instagram", "text_content": "Officially entering my 30s today! Born May 14, 1996 and loving the journey so far 🎉", "location_tag": "San Francisco, CA", "media_type": "photo"},
        {"profile_id": "C", "post_id": "SOC_C02", "timestamp": "2026-04-05T15:00:00Z", "platform": "instagram", "text_content": "Happy 3rd birthday to my favorite golden retriever, Barnaby! Best hiking partner ever 🐶", "location_tag": "Marin Headlands", "media_type": "photo"},
        {"profile_id": "C", "post_id": "SOC_C03", "timestamp": "2026-03-22T19:00:00Z", "platform": "facebook", "text_content": "Great catching up with old classmates at the Oakfield Elementary 20-year alumni picnic! Can't believe it's been that long.", "location_tag": "Oakfield Park", "media_type": "photo"},
    ]

    _write_csv("social_posts.csv", [
        "profile_id", "post_id", "timestamp", "platform", "text_content", "location_tag", "media_type"
    ], social_posts)

    # -------------------------------------------------------------------------
    # 6. pharmacy_orders
    # -------------------------------------------------------------------------
    pharmacy_orders = [
        # Profile A: Routine OTC vitamins
        {"profile_id": "A", "order_id": "PHM_A01", "timestamp": "2026-04-10T10:00:00Z", "item_category": "Daily Multivitamin 100ct", "prescriber_specialty": "General Wellness", "delivery_address": "742 Evergreen Terr, Springfield"},
        {"profile_id": "A", "order_id": "PHM_A02", "timestamp": "2026-05-12T11:00:00Z", "item_category": "Ibuprofen 200mg", "prescriber_specialty": "General Wellness", "delivery_address": "742 Evergreen Terr, Springfield"},

        # Profile B: Sensitive specialty categories (Immunology / Oncology supportive care)
        {"profile_id": "B", "order_id": "PHM_B01", "timestamp": "2026-05-06T09:30:00Z", "item_category": "Immunology Supportive Therapy", "prescriber_specialty": "Hematology-Oncology", "delivery_address": "404 Meadow Lane, Detroit"},
        {"profile_id": "B", "order_id": "PHM_B02", "timestamp": "2026-05-20T10:15:00Z", "item_category": "Targeted Anti-Emetic Formulation", "prescriber_specialty": "Hematology-Oncology", "delivery_address": "404 Meadow Lane, Detroit"},
        {"profile_id": "B", "order_id": "PHM_B03", "timestamp": "2026-06-03T11:00:00Z", "item_category": "Immunology Supportive Therapy", "prescriber_specialty": "Hematology-Oncology", "delivery_address": "404 Meadow Lane, Detroit"},

        # Profile C: Allergy medication
        {"profile_id": "C", "order_id": "PHM_C01", "timestamp": "2026-03-15T14:00:00Z", "item_category": "Cetirizine 10mg Anti-Allergy", "prescriber_specialty": "Allergy & Asthma", "delivery_address": "88 Clipper St, San Francisco"},
    ]

    _write_csv("pharmacy_orders.csv", [
        "profile_id", "order_id", "timestamp", "item_category", "prescriber_specialty", "delivery_address"
    ], pharmacy_orders)

    # -------------------------------------------------------------------------
    # 7. Ground Truth Dataset (data/ground_truth.json)
    # -------------------------------------------------------------------------
    ground_truth = [
        # --- PROFILE A (Location & Routine) ---
        {
            "profile_id": "A",
            "inference_id": "A_INF_HOME_ADDR",
            "claim": "Home address is 742 Evergreen Terr, Springfield",
            "category": "location",
            "expected_label": "supported",
            "required_fact_refs": [
                {"table": "food_orders", "key_col": "delivery_address", "value": "742 Evergreen Terr, Springfield"},
                {"table": "strava_activities", "key_col": "start_lat", "value": "39.7817"}
            ]
        },
        {
            "profile_id": "A",
            "inference_id": "A_INF_MORNING_ROUTINE",
            "claim": "Follows a regular weekday morning running routine between 06:30 and 07:15 AM",
            "category": "routine",
            "expected_label": "supported",
            "required_fact_refs": [
                {"table": "strava_activities", "key_col": "start_time", "value": "06:30:00"},
                {"table": "strava_activities", "key_col": "route_summary", "value": "Morning loop via Elm Park"}
            ]
        },
        {
            "profile_id": "A",
            "inference_id": "A_INF_ABSENCE_WINDOW",
            "claim": "Home is vacant during July 10-20 due to family vacation in Hawaii",
            "category": "absence",
            "expected_label": "supported",
            "required_fact_refs": [
                {"table": "calendar_events", "key_col": "title", "value": "PTO - Annual Hawaii Vacation"},
                {"table": "social_posts", "key_col": "text_content", "value": "Hawaii here we come"}
            ]
        },
        {
            "profile_id": "A",
            "inference_id": "A_INF_DECOY_NIGHTSHIFT",
            "claim": "Works regular night shifts as primary employment",
            "category": "employment",
            "expected_label": "speculation",
            "required_fact_refs": []
        },

        # --- PROFILE B (Sensitive Medical & Insurer Exposure) ---
        {
            "profile_id": "B",
            "inference_id": "B_INF_SPECIALIST_VISITS",
            "claim": "Attends regular bi-weekly specialist consultations at Oakridge Oncology & Hematology Suite 400",
            "category": "health_exposure",
            "expected_label": "supported",
            "required_fact_refs": [
                {"table": "calendar_events", "key_col": "location", "value": "Oakridge Oncology & Hematology Suite 400"},
                {"table": "calendar_events", "key_col": "title", "value": "Infusion Therapy Session"}
            ]
        },
        {
            "profile_id": "B",
            "inference_id": "B_INF_INSURER_EXPOSURE",
            "claim": "Chronic immunology and oncology supportive treatments present underwriting and insurer-relevant exposure risk",
            "category": "financial_insurer",
            "expected_label": "weakly_supported",
            "required_fact_refs": [
                {"table": "pharmacy_orders", "key_col": "prescriber_specialty", "value": "Hematology-Oncology"},
                {"table": "pharmacy_orders", "key_col": "item_category", "value": "Immunology Supportive Therapy"}
            ]
        },
        {
            "profile_id": "B",
            "inference_id": "B_INF_DECOY_CONDITION",
            "claim": "Clinically diagnosed with Stage 3 Diffuse Large B-cell Lymphoma",
            "category": "health_diagnosis",
            "expected_label": "speculation",
            "required_fact_refs": []
        },

        # --- PROFILE C (Account Takeover / KBA Security Answers) ---
        {
            "profile_id": "C",
            "inference_id": "C_INF_DOB",
            "claim": "Date of birth is May 14, 1996",
            "category": "identity_kba",
            "expected_label": "supported",
            "required_fact_refs": [
                {"table": "social_posts", "key_col": "text_content", "value": "Born May 14, 1996"},
                {"table": "calendar_events", "key_col": "title", "value": "My 30th Birthday Dinner!"}
            ]
        },
        {
            "profile_id": "C",
            "inference_id": "C_INF_PET_NAME",
            "claim": "Pet dog name is Barnaby (Golden Retriever)",
            "category": "identity_kba",
            "expected_label": "supported",
            "required_fact_refs": [
                {"table": "social_posts", "key_col": "text_content", "value": "golden retriever, Barnaby"},
                {"table": "calendar_events", "key_col": "title", "value": "Barnaby Vet Annual Checkup"}
            ]
        },
        {
            "profile_id": "C",
            "inference_id": "C_INF_FIRST_SCHOOL",
            "claim": "First school attended was Oakfield Elementary",
            "category": "identity_kba",
            "expected_label": "weakly_supported",
            "required_fact_refs": [
                {"table": "social_posts", "key_col": "text_content", "value": "Oakfield Elementary 20-year alumni picnic"}
            ]
        },
        {
            "profile_id": "C",
            "inference_id": "C_INF_DECOY_MAIDEN_NAME",
            "claim": "Mother's maiden name is Vance",
            "category": "identity_kba",
            "expected_label": "speculation",
            "required_fact_refs": []
        }
    ]

    GROUND_TRUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GROUND_TRUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"[generate_synthetic] Generated 6 CSV tables in {SAMPLE_DIR}")
    print(f"[generate_synthetic] Generated ground truth at {GROUND_TRUTH_FILE}")


def _write_csv(filename: str, fieldnames: list[str], rows: list[dict]) -> None:
    path = SAMPLE_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    generate_all()
