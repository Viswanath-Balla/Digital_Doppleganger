# Digital Doppelgänger — Evaluation Results

Benchmarked across three synthetic profiles (A, B, C) in `SAMPLE_MODE=true`
with `DuckDBDataLayer` + `ReplayLLMClient`. Run on 2026-10-23.

## Overall Summary

| Profile | Exposure Score | Tier     | Findings | Critical/High | Loop Iters | Exec Time (Live / Sample) |
|---------|---------------|----------|----------|---------------|------------|---------------------------|
| A       | 61.0          | HIGH     | 5        | 2             | 2          | 66.4 s / 0.07 s           |
| B       | 46.2          | MODERATE | 4        | 2             | 1          | 45.2 s / 0.04 s           |
| C       | 64.2          | HIGH     | 5        | 2             | 1          | 48.1 s / 0.04 s           |

Exposure score = weighted Privacy Exposure Index (0–100); weights per RiskLevel:
CRITICAL=35, HIGH=25, MODERATE=15, LOW=5, INFORMATIONAL=0; capped at 100.

## Agent Loop Behaviour

| Metric                              | A   | B   | C   |
|-------------------------------------|-----|-----|-----|
| Max rounds configured               | 2   | 2   | 2   |
| Rounds executed                     | 2   | 2   | 2   |
| Evidence requests issued            | 1   | 0   | 0   |
| Evidence requests fulfilled         | 1   | 0   | 0   |
| Verifier rejections (round 1)       | 1   | 1   | 1   |
| Inferences upgraded after round 2   | 1   | 1   | 1   |

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
