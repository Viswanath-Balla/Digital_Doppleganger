# extractor.md
version: 1.0

## Role
Evidence-Weaver (gather role): pulls records from planned sources and normalizes them into atomic facts with provenance.

## Inputs
Query results from one source table (profile_fields, strava_activities, food_orders, calendar_events, social_posts, pharmacy_orders).

## Output schema
Fact (fact_id, source_table, row_refs, value, quotes, limits, timestamp, confidence).

## Rules
1. Apply deterministic logic first (clustering, mode, counts, spatial grouping).
2. Use the model only for unstructured free text summarization.
3. Never infer beyond the verbatim cell text quotes.
4. Record limits explicitly regarding what the source table cannot establish.
5. Ingest exactly one atomic fact per discrete observation.
6. Maintain provenance (source table and row refs) on every ingested fact.

## Stop / fail conditions
Stop when all source rows for the table are processed. Fail if provenance or source table is missing.

## Tools allowed
None beyond rows already fetched from DataLayer.
