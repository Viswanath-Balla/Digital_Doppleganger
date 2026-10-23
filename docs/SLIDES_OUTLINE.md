# Digital Doppelgänger — Pitch Deck Slide Outline 📊

This outline serves as the blueprint for creating the submission slide deck (10–12 slides) for hackathon evaluation and presentations.

---

### Slide 1: Title & Tagline
* **Title**: Digital Doppelgänger 👤🔍
* **Subtitle**: Multi-Agent Adversarial Privacy Auditing: What can adversaries infer by combining your scattered digital fragments?
* **Presenter / Team**: Viswanath Balla
* **Visual**: Clean, dark-mode graphic representing a fragmented digital identity recombined into an adversarial shadow profile ("Doppelgänger").

---

### Slide 2: The Problem — The Cross-Silo Privacy Paradox
* **Key Point**: No single platform exposes you; their combination destroys your privacy.
* **The Reality**:
  * Strava knows where you run in the morning.
  * Uber Eats knows where you order dinner at night.
  * Google Calendar knows when you are away from home.
  * LinkedIn and Instagram know your coworkers, family, and high school.
* **The Danger**: Modern adversaries (stalkers, burglars, social engineers, automated OSINT scrapers) connect these breadcrumbs across silos to infer home addresses, predictable absence schedules, and security question answers.
* **Visual**: Four isolated cloud icons (Strava, Food Delivery, Calendar, Social) each marked "Looks Safe" -> Red arrows converging into a high-risk bullseye: "Physical Residence & Routine Leaked".

---

### Slide 3: Target Users & Market Need
* **Who Needs This?**:
  1. **Individuals & High-Profile Executives**: Protect physical safety, family whereabouts, and routine predictability.
  2. **Security & Privacy Auditors (DPOs)**: Quantify composite risk across enterprise SaaS applications and API integrations.
  3. **OSINT Defense Researchers**: Study multi-agent cross-correlation capabilities under rigorous conditions.
  4. **Everyday Digital Citizens**: Understand their true attack surface and receive concrete, low-effort fixes.
* **Callout**: *"Traditional privacy tools tell you what data exists. Digital Doppelgänger tells you what that data reveals."*

---

### Slide 4: The Solution — Defensive Adversarial Red-Teaming
* **Core Philosophy**: Fight adversarial AI with adversarial AI.
* **How It Works**:
  * An automated **Red-Team Agent** searches for privacy leakage chains like an attacker.
  * An adversarial **Verifier Agent** audits every claim to eliminate hallucinations and demands corroborating evidence.
  * A **Counterfactual Remediation Engine** computes the minimal linchpin fact to break the chain.
* **Visual**: Split slide showing "Offensive Reconnaissance Simulation" vs. "Defensive Causal Remediation".

---

### Slide 5: Agent Workflow & Architecture
* **Orchestration Flow**:
  1. **Planner**: Identifies data sources and scopes queries.
  2. **Extractor**: Normalizes raw records into atomic facts with cryptographic provenance.
  3. **Linker**: Uncovers cross-source entity linkages (spatio-temporal clusters, shared identifiers).
  4. **Red-Team (`Nemotron-4-340B`)**: Synthesizes adversarial inferences.
  5. **Verifier (`Nemotron-4-340B`)**: Audits claims -> Rejects -> Requests targeted evidence -> Upgrades substantiated findings.
* **Visual**: Clean mermaid/system diagram showing the feedback loop between Extractor, Red-Team, Verifier, and the Meterless World Model.

---

### Slide 6: Technology Stack & Foundation
* **Multi-Agent Engine**: Python 3.11, Pydantic v2, AsyncIO, NetworkX graph modeling.
* **LLM Reasoning**: NVIDIA Nemotron-4-340B-Instruct via Nightshift enterprise proxy.
* **Federated Data**: Zetaris Virtual Data Warehouse (PostgreSQL wire protocol / JDBC).
* **Zero-Config Offline Fallback**: In-memory DuckDB + deterministic Replay LLM client.
* **Web Experience**: FastAPI REST API + Pure Vanilla CSS/JS design-taste frontend (zero heavy frontend framework build steps).
* **Visual**: Modern stack badge grid (Python, DuckDB, Zetaris, NVIDIA, Nightshift, FastAPI).

---

### Slide 7: Sponsor Technology Deep-Dive: Zetaris & Meterless
* **Zetaris Virtual Data Warehouse**:
  * **Zero Data Centralization**: Queries data directly at external source points without building a centralized honey-pot database.
  * **Cross-Source Virtual Joins**: Pushes down queries across Strava, calendar, delivery, and social feeds.
* **Meterless World Model**:
  * **Immutable Provenance Graph**: Every fact retains source table, column, row ID, and timestamp lineage.
  * **Zero Token Metering Overhead**: In-memory fact index prevents repetitive, expensive prompt flooding.
  * **Verified Quality**: 100% passing tests in `tests/test_world_model.py`.

---

### Slide 8: What Makes Digital Doppelgänger Unique?
* **1. Adversarial Duel, Not Summarization**: Instead of naive prompt summaries, a two-player game grounds every finding in verified truth.
* **2. Eliminates Hallucinations**: Verifier rejects unsupported claims (0% false positives on uncorroborated decoys in eval benchmarks).
* **3. Counterfactual Linchpin Remediation**: Pinpoints the exact 1–2 data points to delete or obscure to collapse the entire inference graph.
* **4. Complete Local Privacy**: Operates fully in-memory and can run 100% offline in Sample Mode.
* **Visual**: Comparison matrix: Traditional Scanners vs. LLM Wrappers vs. Digital Doppelgänger.

---

### Slide 9: Product Experience & Live Visuals
* **Design Philosophy**: Crafted with anti-slop, high-information-density aesthetics (`design-taste-frontend`).
* **Key Interfaces**:
  * **Run & Monitor**: Profile selection, explicit consent gate, real-time KPI banner.
  * **Findings Tab**: Risk-sorted cards with verdict badges (`supported`, `weakly_supported`, `speculation`).
  * **Loop Trace Timeline**: Real-time inspection of rejections, queries, and Nemotron decisions.
  * **Remediation & Score Delta**: Interactive before/after exposure gauge (52.5 -> 21.0).
  * **Interactive Evidence Graph**: Visual entity and fact dependency graph.
* **Visual**: High-resolution screenshot collage of the Web UI tabs.

---

### Slide 10: Evaluation & Benchmark Results
* **Rigorous Benchmarks**:
  * Tested on 3 synthetic profiles (A: Location, B: Routine, C: Account Takeover).
  * 15 total privacy claims evaluated against ground truth.
* **Key Metrics**:
  * **100% Precision** on supported privacy findings.
  * **0% False Positive Rate** on uncorroborated speculation.
  * **58% Average Exposure Score Reduction** with targeted linchpin excisions.
  * **<10s Execution Time** per full audit run.
  * **83/83 Tests Passing** across unit, loop, and security suites.
* **Visual**: Clean summary data table from `eval/results.md`.

---

### Slide 11: Future Enhancements & Roadmap
* **Federated Connectors**: Direct OAuth plugins for Google Takeout, Apple Health, Strava API, and Mastodon/Bluesky.
* **Differential Privacy Obfuscation**: Automated injection of synthetic decoy records to poison adversarial inference models.
* **Automated Data Deletion API (GDPR / CCPA / RTBF)**: One-click deletion requests sent directly to data brokers and platforms for identified linchpin facts.
* **Enterprise Multi-Tenant Mode**: Continuous organizational employee exposure monitoring with enterprise SSO.

---

### Slide 12: Summary & Links
* **Repository**: [https://github.com/Viswanath-Balla/Digital_Doppleganger](https://github.com/Viswanath-Balla/Digital_Doppleganger)
* **Demo Video**: [3-4 Minute Walkthrough](docs/DEMO_SCRIPT.md)
* **Status**: Ready for immediate deployment, 100% reproducible with `SAMPLE_MODE=true`.
* **Closing Quote**: *"You cannot defend what you cannot see. Digital Doppelgänger reveals your composite footprint before adversaries exploit it."*
