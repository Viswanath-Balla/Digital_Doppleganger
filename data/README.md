# Digital Doppelgänger: Synthetic Data & Ground Truth

## 1. Data Source & Provenance
All data stored in `data/sample/` is **100% synthetic**, generated algorithmically using deterministic rules and seeds. No real human personal identifiable information (PII), protected health information (PHI), or location telemetry is used. Names, addresses, routes, medical clinics, and events are purely fictional.

## 2. License
This synthetic dataset is dedicated to the public domain under the **Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication**. You can copy, modify, distribute, and perform the work, even for commercial purposes, all without asking permission.

## 3. Profile Summary & Row Counts

The dataset models three distinct personas (`profile_id`: `A`, `B`, `C`):
- **Profile A (Alex Rivera)**: Location privacy & routine pattern analysis (repetitive GPS running clusters, food deliveries, and absence window leaks).
- **Profile B (Brenda Vance)**: Sensitive medical category exposure (specialist visits and supportive oncology/immunology pharmacy orders without explicit diagnosis).
- **Profile C (Charlie Chen)**: Account takeover & knowledge-based authentication (KBA) exposure (date of birth, pet name, and alumni mentions).

### Current Table Row Counts

| Table Name | File | Total Rows | Profile A | Profile B | Profile C |
|---|---|---|---|---|---|
| `profile_fields` | `profile_fields.csv` | 16 | 6 | 5 | 5 |
| `strava_activities` | `strava_activities.csv` | 14 | 9 | 3 | 2 |
| `food_orders` | `food_orders.csv` | 11 | 7 | 2 | 2 |
| `calendar_events` | `calendar_events.csv` | 11 | 5 | 4 | 2 |
| `social_posts` | `social_posts.csv` | 8 | 3 | 2 | 3 |
| `pharmacy_orders` | `pharmacy_orders.csv` | 6 | 2 | 3 | 1 |
| **Total** | | **66** | **32** | **19** | **15** |

Each profile contains 15–35 rows across sources, satisfying the target footprint (compact, human-auditable, and high density of cross-source linkages).

## 4. Ground Truth Schema (`data/ground_truth.json`)

Ground-truth privacy inferences are structured as:
```json
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
}
```

Labels:
- `supported`: Definitively proven by multi-source correlation.
- `weakly_supported`: Probable based on circumstantial evidence or partial correlation.
- `speculation`: Decoy claim with insufficient, conflicting, or zero corroborating evidence.

## 5. How Zetaris Registers Tables

In live mode, Zetaris Virtual Data Warehouse mounts these CSV files via virtual table DDL.
See [`scripts/register_zetaris_sources.sql`](scripts/register_zetaris_sources.sql) for table definitions and location clauses.

In sample mode (`SAMPLE_MODE=true`), [`DuckDBDataLayer`](src/dd/adapters/duckdb_data_layer.py) mounts these tables directly in an embedded, in-memory DuckDB database with identical table schemas.

## 6. Regeneration Steps

To deterministically re-create all CSV tables and ground truth:
```bash
python scripts/generate_synthetic.py
```
This produces identical files across runs (fixed seed and deterministic ordering).
