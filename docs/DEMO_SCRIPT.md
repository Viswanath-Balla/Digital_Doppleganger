# Digital Doppelgänger — 3 to 4 Minute Video Demo Script 🎬

**Target Duration**: 3:50 – 4:00 minutes  
**Presenter**: Video Narrator / Screen Demonstrator  
**Setup**: Browser open at `http://localhost:7860` (or demo recording setup), terminal ready with live logs.

---

### [0:00 - 0:25] The Problem: The Cross-Silo Privacy Paradox
* **Visual**: Camera on presenter or title card showing "Digital Doppelgänger: Multi-Agent Privacy Audit", transitioning to animated slides or browser showing modern data silos (Strava icon, Uber Eats icon, Calendar, LinkedIn).
* **Narrator (Spoken)**:
  > *"Every day, we leave fragments of our lives across dozens of apps: a morning jog logged on Strava, an occasional takeout order on Uber Eats, an out-of-office block on our work calendar, or a casual high school reunion post on social media.*  
  > *In isolation, each of these data points looks completely benign and anonymized. But sophisticated adversaries, stalkers, and automated OSINT bots don't look at platforms in isolation—they connect the dots across silos.*  
  > *This is Digital Doppelgänger: an adversarial multi-agent privacy auditing system that acts as your personal defensive red team to discover what an adversary can infer about you before they do."*

---

### [0:25 - 1:15] Consent Gate & Running Profile A
* **Visual**: Switch to browser screen at `http://localhost:7860`. The "01 Run & Monitor" tab is active. The narrator points to the Mode badge in the top bar ("Sample Mode · DuckDB + Nemotron Replay") and the Profile dropdown.
* **Narrator (Spoken)**:
  > *"Let's look at the live application. First, notice our ethical safeguards. Because privacy auditing is a dual-use capability, we enforce a mandatory consent gate. An audit cannot execute without explicit confirmation that the data is synthetic or belongs to the user.*  
  > *We select **Profile A: Alex Rivera**—a synthetic profile representing a typical tech professional.*  
  > *We check the consent box, and click **Run Privacy Audit**.*  
  > *Watch the live execution: in real time, our Planner dispatches queries to our federated data layer, normalizes records into an in-memory knowledge model, and launches an adversarial duel between our Red-Team and Verifier agents."*
* **Visual**: Click "Run Privacy Audit". Progress bar sweeps, status card shows "Audit complete — Profile A", and KPI strip updates to show Exposure Score: 52.5 / 100 (HIGH), 5 findings, 2 Critical/High.

---

### [1:15 - 2:00] Loop Trace: Verifier Rejection -> Zetaris Evidence Query -> Upgraded Finding
* **Visual**: Click on the **"03 Agent Loop Trace"** tab. Scroll through the chronological agent message timeline.
* **Narrator (Spoken)**:
  > *"Here is what makes Digital Doppelgänger unique: it's not a single prompt or a simple summary. It is an iterative adversarial game.*  
  > *Look at Round 1 in the trace: our Red-Team agent, powered by NVIDIA Nemotron, hypothesized that Alex Rivera's private home residence is 742 Evergreen Terrace.*  
  > *Immediately, our Verifier agent stepped in and **rejected** the claim! The Verifier noted: 'Single food delivery address is insufficient without spatial corroboration.'*  
  > *Instead of giving up or hallucinating, the Verifier triggered a targeted follow-up query to Zetaris Virtual Data Warehouse, demanding Strava GPS activity coordinates.*  
  > *In Round 2, the newly retrieved GPS start and end coordinates matched the exact coordinates of the delivery address. The Verifier upgraded the finding from 'speculation' to 'supported' with 94% confidence! This eliminates hallucinations while catching composite leaks."*
* **Visual**: Highlight the yellow "rejected" badge in Round 1, the green Zetaris SQL query line, and the green "UPGRADED" / "supported" badge in Round 2.

---

### [2:00 - 2:30] Evidence Chain & Vulnerability Findings
* **Visual**: Click on the **"02 Vulnerability Findings"** tab. Show the 5 finding cards sorted by risk level. Click on the top finding: "Home address inferrable from Strava start/end + food delivery coordinates".
* **Narrator (Spoken)**:
  > *"On the Findings tab, every discovery is ranked by risk level with clear verdict badges.*  
  > *If we expand our top finding—home address exposure—we see the complete evidence chain.*  
  > *Notice the interconnected nodes: Fact 260 from the food delivery table, correlated with GPS start and end clusters from Strava activities. The system also flags the attacker model: physical stalkers and doxxers.*  
  > *We also see secondary findings: Alex's regular evening absence schedule and employer identification."*
* **Visual**: Expand the evidence chain, showing the interactive SVG/graph view in tab 06 for visual punch.

---

### [2:30 - 3:00] Remediation & Counterfactual Score Delta
* **Visual**: Click on the **"04 Remediation & Delta"** tab. Focus on the before/after exposure gauge and the Linchpin analysis card.
* **Narrator (Spoken)**:
  > *"Most privacy tools overwhelm users by saying 'delete all your accounts.' Digital Doppelgänger does something far smarter: **counterfactual linchpin analysis**.*  
  > *Our engine analyzes the causal graph in the Meterless world model to compute the minimal cut set. It asks: 'What is the single smallest action the user can take to break this inference chain?'*  
  > *Look at the result: simply enabling privacy zones on Strava to obscure the first 500 meters of runs breaks the link to the delivery address.*  
  > *This single action causes the adversary's inference to collapse, dropping Alex's Privacy Exposure Score from **52.5 down to 21.0**—a massive 60% risk reduction with minimal effort!"*

---

### [3:00 - 3:30] Evaluation Benchmarks & Ground-Truth Verification
* **Visual**: Click on the **"05 System Evaluation"** tab, displaying the rendered `eval/results.md` benchmark table.
* **Narrator (Spoken)**:
  > *"Under the Evaluation tab, you can inspect our rigorous benchmark results across all three synthetic personas (Profiles A, B, and C).*  
  > *Across all 15 privacy claims, our Verifier achieved **100% precision** on supported claims and a **0% false positive rate** on uncorroborated speculation.*  
  > *Furthermore, our entire test suite of 83 unit and security tests, including automated secret scanning and clean-clone verification, passes in seconds."*

---

### [3:30 - 3:50] Sponsor Technology Proof
* **Visual**: Briefly switch to slide or diagram highlighting the sponsor stack logos: Zetaris, Meterless, Nightshift, NVIDIA Nemotron.
* **Narrator (Spoken)**:
  > *"Digital Doppelgänger brings together the best of modern AI and data architecture:*  
  > *1. **Zetaris Virtual Data Warehouse**: allows federated queries across simulated silos without physically moving or aggregating sensitive user data.*  
  > *2. **Meterless In-Memory World Model**: acts as our immutable provenance store, preventing token waste and anchoring every inference in verifiable facts.*  
  > *3. **Nightshift & NVIDIA Nemotron**: delivers the high-speed, deep reasoning necessary for adversarial red-teaming and rigorous truth verification.*  
  > *And with our zero-config Sample Mode, anyone can clone this repository and run the full suite in under 30 seconds."*

---

### [3:50 - 4:00] Conclusion & Call to Action
* **Visual**: Return to main dashboard view with GitHub repository URL displayed on screen: `github.com/Viswanath-Balla/Digital_Doppleganger`.
* **Narrator (Spoken)**:
  > *"Digital Doppelgänger turns the power of adversarial AI into your greatest privacy defense. Check out the code, run the audit, and protect your digital twin. Thank you!"*
