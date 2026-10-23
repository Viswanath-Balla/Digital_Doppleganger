"""Tests for synthetic data generation, ground-truth validity, and DuckDBDataLayer.

Verifies:
  1. Data generation determinism across runs.
  2. DuckDBDataLayer health check and table initialization.
  3. All planted leaks have their required facts present in the data.
  4. Decoys do not have corroborating evidence.
  5. Multi-table SQL join query executes cleanly for Profile A.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

import pytest

from scripts.generate_synthetic import generate_all
from src.dd.adapters.duckdb_data_layer import DuckDBDataLayer

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT_DIR / "data" / "sample"
GROUND_TRUTH_FILE = ROOT_DIR / "data" / "ground_truth.json"


@pytest.fixture(scope="module")
def data_layer() -> DuckDBDataLayer:
    """Fixture providing an active DuckDBDataLayer."""
    dl = DuckDBDataLayer(sample_data_dir=SAMPLE_DIR)
    yield dl
    dl.close()


class TestSyntheticDataDeterminism:
    """Verify data generator is strictly reproducible."""

    def test_determinism_across_runs(self) -> None:
        generate_all()
        hashes_first = {
            f.name: hashlib.sha256(f.read_bytes()).hexdigest()
            for f in SAMPLE_DIR.glob("*.csv")
        }
        gt_hash_first = hashlib.sha256(GROUND_TRUTH_FILE.read_bytes()).hexdigest()

        # Re-run generator
        generate_all()
        hashes_second = {
            f.name: hashlib.sha256(f.read_bytes()).hexdigest()
            for f in SAMPLE_DIR.glob("*.csv")
        }
        gt_hash_second = hashlib.sha256(GROUND_TRUTH_FILE.read_bytes()).hexdigest()

        assert hashes_first == hashes_second
        assert gt_hash_first == gt_hash_second


class TestDuckDBDataLayer:
    """Verify DuckDBDataLayer mounting, querying, and joins."""

    def test_health_check(self, data_layer: DuckDBDataLayer) -> None:
        ok = asyncio.run(data_layer.health_check())
        assert ok is True

    def test_all_expected_tables_registered(self, data_layer: DuckDBDataLayer) -> None:
        expected = {
            "profile_fields",
            "strava_activities",
            "food_orders",
            "calendar_events",
            "social_posts",
            "pharmacy_orders",
        }
        assert expected.issubset(set(data_layer.registered_tables))

    def test_sql_join_two_tables_for_profile_a(
        self, data_layer: DuckDBDataLayer
    ) -> None:
        """Core Phase 1 check: Join two tables for Profile A via DuckDBDataLayer."""
        sql = """
            SELECT
                f.profile_id,
                f.delivery_address,
                s.start_lat,
                s.start_lon,
                COUNT(*) AS correlation_count
            FROM food_orders f
            JOIN strava_activities s
                ON f.profile_id = s.profile_id
            WHERE f.profile_id = 'A'
            GROUP BY f.profile_id, f.delivery_address, s.start_lat, s.start_lon
            HAVING correlation_count > 0
            ORDER BY correlation_count DESC;
        """
        rows = asyncio.run(data_layer.query(sql))
        assert len(rows) > 0
        first_row = rows[0]
        assert first_row["profile_id"] == "A"
        assert "742 Evergreen Terr" in first_row["delivery_address"]
        assert first_row["start_lat"] == pytest.approx(39.7817, abs=1e-3)
        assert first_row["correlation_count"] > 0


class TestGroundTruthValidation:
    """Verify ground truth planted leaks and decoys against the actual data."""

    @pytest.fixture(scope="class")
    def ground_truth(self) -> list[dict]:
        with open(GROUND_TRUTH_FILE, encoding="utf-8") as f:
            return json.load(f)

    def test_planted_leaks_have_required_facts_in_data(
        self, data_layer: DuckDBDataLayer, ground_truth: list[dict]
    ) -> None:
        """Every supported / weakly_supported leak must find its required facts in the DB."""
        for item in ground_truth:
            if item["expected_label"] in ("supported", "weakly_supported"):
                pid = item["profile_id"]
                assert len(item["required_fact_refs"]) > 0, (
                    f"Leak {item['inference_id']} has expected_label={item['expected_label']} "
                    f"but empty required_fact_refs"
                )
                for ref in item["required_fact_refs"]:
                    table = ref["table"]
                    key_col = ref["key_col"]
                    expected_val = ref["value"]

                    # Query to verify fact exists in the data
                    query_sql = f"""
                        SELECT COUNT(*) AS c
                        FROM {table}
                        WHERE profile_id = '{pid}'
                          AND CAST({key_col} AS VARCHAR) LIKE '%{expected_val}%';
                    """
                    res = asyncio.run(data_layer.query(query_sql))
                    assert res[0]["c"] > 0, (
                        f"Fact missing for {item['inference_id']}: {table}.{key_col} "
                        f"containing '{expected_val}' for profile {pid}"
                    )

    def test_decoys_lack_factual_corroboration(
        self, data_layer: DuckDBDataLayer, ground_truth: list[dict]
    ) -> None:
        """Decoys marked speculation must have no planted fact references."""
        for item in ground_truth:
            if item["expected_label"] == "speculation":
                assert item["required_fact_refs"] == []

        # Negative checks on specific decoy claims
        # 1. Profile A decoy: "works night shifts" - no regular night shifts in calendar
        night_cal = asyncio.run(
            data_layer.query(
                "SELECT COUNT(*) AS c FROM calendar_events "
                "WHERE profile_id = 'A' AND LOWER(title) LIKE '%night%';"
            )
        )
        assert night_cal[0]["c"] == 0

        # 2. Profile B decoy: "Stage 3 Lymphoma" - no clinical diagnosis in pharmacy or calendar
        lymphoma_check = asyncio.run(
            data_layer.query(
                "SELECT COUNT(*) AS c FROM pharmacy_orders "
                "WHERE profile_id = 'B' AND LOWER(item_category) LIKE '%lymphoma%';"
            )
        )
        assert lymphoma_check[0]["c"] == 0

        # 3. Profile C decoy: "Mother's maiden name is Vance" - never mentioned
        maiden_check = asyncio.run(
            data_layer.query(
                "SELECT COUNT(*) AS c FROM profile_fields "
                "WHERE profile_id = 'C' AND LOWER(field_value) LIKE '%vance%';"
            )
        )
        assert maiden_check[0]["c"] == 0
