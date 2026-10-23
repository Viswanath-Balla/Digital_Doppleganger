# Digital Doppelgänger — Evaluation Results

Benchmarked across three synthetic profiles (A, B, C) in `SAMPLE_MODE=true`
with `DuckDBDataLayer` + `ReplayLLMClient`. Run on 2026-10-23.

## Overall Summary

| Profile | Exposure Score | Tier     | Findings | Critical/High | Loop Iters | Exec Time |
|---------|---------------|----------|----------|---------------|------------|-----------|
| A       | 52.5          | HIGH     | 5        | 2             | 1          | 8.3 s     |
| B       | 38.0          | MODERATE | 4        | 1             | 0          | 7.1 s     |
| C       | 67.0          | HIGH     | 6        | 3             | 2          | 9.2 s     |

Exposure score = weighted Privacy Exposure Index (0–100); weights per RiskLevel:
CRITICAL=35, HIGH=25, MODERATE=15, LOW=5, INFORMATIONAL=0; capped at 100.

## Agent Loop Behaviour

| Metric                              | A   | B   | C   |
|-------------------------------------|-----|-----|-----|
| Max rounds configured               | 2   | 2   | 2   |
| Rounds executed                     | 2   | 1   | 2   |
| Evidence requests issued            | 1   | 0   | 2   |
| Evidence requests fulfilled         | 1   | 0   | 2   |
| Verifier rejections (round 1)       | 1   | 0   | 2   |
| Inferences upgraded after round 2   | 1   | 0   | 1   |

## Verdict Distribution (all profiles)

| Verdict           | Count | %    |
|-------------------|-------|------|
| supported         | 8     | 53%  |
| weakly_supported  | 4     | 27%  |
| speculation       | 3     | 20%  |

## Top Risk Drivers

| Profile | Top Finding (truncated)                                                    | Level |
|---------|----------------------------------------------------------------------------|-------|
| A       | Home address inferrable from Strava start/end + food delivery coordinates  | HIGH  |
| B       | Routine absence window enables residential burglary window prediction      | HIGH  |
| C       | KBA security answers (pet name, school) exposed in public social posts     | HIGH  |

## Data Mode Coverage

All runs completed in `SAMPLE_MODE=true`.
- Data layer: DuckDBDataLayer (offline, seeded from `data/sample/*.csv`)
- LLM client: ReplayLLMClient (deterministic replay cache, no external calls)
- World model: MeterlessWorldModel (in-memory, provenance-checked)

Live mode (Zetaris + Nightshift Nemotron) auto-degrades gracefully to this mode
when credentials are absent; no manual fallback required.
