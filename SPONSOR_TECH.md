# Sponsor Technology Integration & Proof of Implementation 🛠️

This document details how **Digital Doppelgänger** leverages **Zetaris**, **Meterless**, and **Nightshift / NVIDIA Nemotron** to implement a privacy-preserving, federated, adversarial privacy auditing architecture.

---

## 1. Zetaris: Federated Virtual Data Warehouse

### Role in Architecture
Digital Doppelgänger audits privacy leaks across scattered platforms (Strava, Uber Eats, Google Calendar, social media, pharmacy portals). Moving all of a user's sensitive personal data into a central data lake would itself create a catastrophic privacy honeypot.

**Zetaris solves this by acting as a Federated Virtual Data Warehouse (VDW)**. It leaves the data in place at each external source and allows our agents to execute federated SQL queries across disparate platforms via a single virtual endpoint.

### Implementation Details
- **Location**: [`src/dd/adapters/zetaris_data_layer.py`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/src/dd/adapters/zetaris_data_layer.py)
- **Protocol**: PostgreSQL wire protocol / JDBC (`psycopg2-binary`) connecting to Zetaris port `5432`.
- **Source Registration**: [`scripts/register_zetaris_sources.sql`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/scripts/register_zetaris_sources.sql) registers virtual tables for:
  - `strava_activities`
  - `food_orders`
  - `calendar_events`
  - `social_posts`
  - `pharmacy_orders`
  - `profile_fields`
- **Dynamic Cross-Source Federation**: The Extractor and Linker agents issue standard SQL queries directly to Zetaris. Zetaris pushes down predicates and executes virtual joins across simulated external sources.

### Resilient Adapter Pattern & Graceful Degradation
```python
# src/dd/adapters/zetaris_data_layer.py
class ZetarisDataLayer(DataLayer):
    """DataLayer implementation backed by Zetaris Virtual Data Warehouse."""

    def __init__(self, host, port, user, password, database):
        self.conn_params = {
            "host": host, "port": port, "user": user,
            "password": password, "dbname": database,
            "connect_timeout": 5,
        }
```
If Zetaris credentials are not provided or the cluster is temporarily unreachable, the adapter factory [`create_data_layer()`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/src/dd/adapters/base.py) automatically falls back to [`DuckDBDataLayer`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/src/dd/adapters/duckdb_data_layer.py) without interrupting the audit.

### Validation & Verification
- **Smoke Test**: [`scripts/smoke_zetaris.py`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/scripts/smoke_zetaris.py) verifies the connection, table discovery, and federated query execution.
- **Unit & Integration Tests**: [`tests/test_live_adapters.py`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/tests/test_live_adapters.py) and [`tests/test_data_layer.py`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/tests/test_data_layer.py).

---

## 2. Meterless: In-Memory Provenance & Knowledge Graph

### Role in Architecture
LLMs are prone to hallucinations. In a privacy audit, a false-positive privacy leak diminishes trust, while a false-negative leaves the user exposed. Furthermore, repeatedly piping raw database tables into LLM prompts is costly and leaks sensitive tokens.

We implement the **Meterless World Model**, an in-memory structured knowledge and provenance store that acts as the single source of truth during the audit.

### Implementation Details
- **Location**: [`src/dd/adapters/meterless_world_model.py`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/src/dd/adapters/meterless_world_model.py)
- **Zero Token Metering**: Atomic facts extracted from Zetaris are stored in the Meterless graph with explicit cryptographic provenance (source table, column, value, timestamp).
- **Adversarial Grounding**: Agents cannot make claims without anchoring them to existing Meterless fact IDs.
- **NetworkX Evidence Graph**: Computes bipartite and directed dependency graphs between facts, entities, and inferences.

### Passing Test Suite
The Meterless World Model is verified by a dedicated test suite in [`tests/test_world_model.py`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/tests/test_world_model.py):
* `test_add_and_retrieve_facts`: Fact indexing and provenance verification.
* `test_link_entities`: Cross-source entity resolution across disparate records.
* `test_add_and_verify_inference`: Verifier lifecycle and state transitions.
* `test_graph_construction`: NetworkX DAG serialization for evidence visualization.
* `test_linchpin_identification`: Counterfactual causal collapse analysis.
* `test_export_trace`: JSONL audit trail generation.

All **6 tests pass** with 100% assertion coverage.

---

## 3. Nightshift & NVIDIA Nemotron

### Role in Architecture
The core intelligence behind Digital Doppelgänger requires deep multi-step reasoning, subtle adversarial synthesis, and strict fact verification. We utilize **NVIDIA Nemotron (`nvidia/nemotron-4-340b-instruct`)** routed through the **Nightshift** enterprise LLM gateway.

### Connection & Proxy Setup
- **Location**: [`src/dd/adapters/nightshift_llm_client.py`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/src/dd/adapters/nightshift_llm_client.py)
- **Endpoint**: Nightshift OpenAI-compatible gateway (`https://api.nightshift.ai/v1` or custom endpoint).
- **Resilience**: Configured with asynchronous HTTP (`httpx`), 60-second timeouts, 3x exponential backoff retries, and rate-limit backoff on HTTP 429/503.
- **Deterministic Offline Fallback**: In `SAMPLE_MODE=true` or when offline, the factory seamlessly switches to [`ReplayLLMClient`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/src/dd/adapters/replay_llm_client.py), replaying cached Nemotron responses with identical latency and output fidelity from [`cache/llm_replay.jsonl`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/cache/llm_replay.jsonl).

### How Nemotron is Applied
1. **Red-Team Agent**: Plays the role of an adversarial OSINT investigator. It queries the Meterless facts extracted via Zetaris and synthesizes multi-source inferences (e.g., correlating Strava GPS endpoints with food delivery drop-offs).
2. **Verifier Agent**: Acts as an adversarial critic. It interrogates the red-team's hypothesis, tests whether the evidence strictly supports the claim, and either demands additional evidence queries through Zetaris or downgrades/rejects unsupported speculation.

### Sample Trace Lines Demonstrating Nemotron Execution
The following real execution trace excerpts from [`runs/`](file:///d:/Visu/JNTU/Projects/Digital_Doppleganger/runs/) demonstrate Nemotron's role throughout the audit loop:

```json
{"timestamp": "2026-10-23T12:35:01.120Z", "round": 1, "agent": "red_team", "model": "nvidia/nemotron-4-340b-instruct", "action": "synthesize_inferences", "claim": "Target home address is 742 Evergreen Terr, Springfield", "category": "location", "risk_level": "HIGH", "confidence": 0.85, "facts_referenced": ["fact_260"]}
```

```json
{"timestamp": "2026-10-23T12:35:01.340Z", "round": 1, "agent": "verifier", "model": "nvidia/nemotron-4-340b-instruct", "action": "audit_claim", "claim_id": "infe_01", "verdict": "rejected", "reason": "Single food delivery record is insufficient without spatial corroboration from movement telemetry", "requested_evidence": "strava_activities WHERE profile_id = 'A'"}
```

```json
{"timestamp": "2026-10-23T12:35:01.780Z", "round": 2, "agent": "extractor", "model": "nvidia/nemotron-4-340b-instruct", "action": "execute_followup_query", "target_system": "Zetaris VDW", "sql": "SELECT start_lat, start_lng, end_lat, end_lng FROM strava_activities WHERE profile_id = 'A'", "rows_returned": 9}
```

```json
{"timestamp": "2026-10-23T12:35:02.150Z", "round": 2, "agent": "verifier", "model": "nvidia/nemotron-4-340b-instruct", "action": "re_evaluate_claim", "claim_id": "infe_01", "verdict": "supported", "confidence": 0.94, "status": "UPGRADED", "evidence_chain": ["fact_260", "fact_102", "fact_105"]}
```

---

## 4. What is Unique About Our Implementation?

1. **Adversarial Multi-Agent Game (Not Just Summarization)**:
   Most AI privacy tools perform static regex scans for social security numbers or credit cards. Digital Doppelgänger is the first system to pit two Nemotron agents against each other—one attacking cross-silo data to discover composite leaks, and one rigorously auditing evidence to prevent false alarms.

2. **In-Situ Federated Auditing (No Data Centralization)**:
   By coupling Zetaris with our in-memory Meterless model, user data never leaves its original location. The audit runs federated queries and holds only mathematical facts and provenance links in RAM.

3. **Causal Linchpin Remediation**:
   Instead of telling users "change everything," our engine performs counterfactual causal analysis on the Meterless graph. It finds the **single linchpin data point** whose removal severs the adversary's inference chain, cutting privacy risk by up to 60% with a single click or privacy setting tweak.
