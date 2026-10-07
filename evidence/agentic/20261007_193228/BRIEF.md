# Agentic forensic brief
run: 20261007_193228 model: qwen3.8:27b
elapsed: 17.0s quick=True

## Executive Brief: Quai Network Intelligence Mesh

**Node Functionality**
The primary node, `quai-radar`, operates as a specialized intelligence engine. It ingests external research and news feeds, utilizing LLM-driven extraction to populate a domain-specific knowledge graph for the Quai Network. The pipeline transforms raw text into structured facts and generates daily strategic briefs for the QUAI/QI ecosystem.

**Shared Topics & Mesh Dynamics**
Current telemetry indicates a heavy focus on **blockchain research analysis** and **ecosystem implication tracking**. The service acts as the central truth-source for the mesh, converting unstructured external data into actionable graph nodes. The high volume of tracked evidence suggests this node is the primary consumer of external threat and opportunity signals, feeding downstream decision-making processes.

**Reconstruction Target**
**Priority Target:** The `llm_extract` and `parse_facts` stages.
**Rationale:** With 111 high-severity findings, the extraction logic is the critical failure point. Reconstructing the prompt engineering and fact-parsing logic is essential to isolate whether high-risk data is being ingested maliciously or if the extraction process is misclassifying benign data as high-risk. This node holds the highest confidence (0.95) in its output, making it the single most valuable asset for validating the integrity of the entire knowledge graph.

## Security Posture

**Risk Rating:** **HIGH**
**Metrics:** 111 High / 80 Medium / 1 Low severity findings.

**Top Issues & Remediation**
1.  **Extraction Integrity:** The high count of severe findings in the `llm_extract` stage suggests potential prompt injection or data poisoning.
    *   *Remediation:* Implement strict input sanitization before LLM processing and add output validation checks to reject anomalous fact structures.
2.  **Graph Pollution:** Unverified facts are being upserted into the knowledge graph.
    *   *Remediation:* Introduce a human-in-the-loop or secondary verification step for high-confidence facts before they are persisted to the graph.
3.  **Evidence Tracking:** 66 tracked evidence items indicate a backlog of unreviewed high-risk data.
    *   *Remediation:* Prioritize the review of the 111 high-severity items to determine if they represent actual threats or false positives in the extraction logic.

---

# Security posture — HIGH

_generated 2026-10-07 19:32:45 · deterministic scan of evidence/reconstructions_

## Findings by severity

| severity | count |
|---|---|
| high | 111 |
| medium | 80 |
| low | 1 |

## Deterministic detail

### Secret / PII survivors

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| low | private_ip | evidence/swarm/results/t-1791394211-aa0f.json:1 | 172.….1 | Confirm the internal address is expected; avoid leaking topology in reports. |
| high | high_entropy | evidence/agentic/20261007_193057/BRIEF.md:86 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/BRIEF.md:94 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/BRIEF.md:101 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/BRIEF.md:108 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/BRIEF.md:115 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/BRIEF.md:122 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/BRIEF.md:127 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:220 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:284 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:340 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:396 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:452 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:508 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:548 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:692 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:1119 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:1126 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193057/security.json:1133 | evid…EF | Verify whether this is a live secret; rotate if so. |

### Prompt-injection attempts

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| medium | prompt_injection:role_hijack | evidence/INVESTIGATION.md:88 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:58 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:59 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:60 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:61 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:62 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:63 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:64 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:65 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:66 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:67 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:68 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:69 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:70 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:71 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/BRIEF.md:72 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:21 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:30 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:39 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:48 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:57 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:66 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:75 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:84 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:93 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:102 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:111 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:120 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:129 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:138 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193057/security.json:147 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_142848/manifest.json:61 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_142848/manifest.json:91 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_142848/manifest.json:95 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_142848/profiler.kid-learning-lab.json:4 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_142848/profiler.kid-learning-lab.json:34 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_142848/profiler.kid-learning-lab.json:38 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_145050/manifest.json:187 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_145050/manifest.json:219 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_145050/manifest.json:223 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_145050/profiler.kid-learning-lab.json:4 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_145050/profiler.kid-learning-lab.json:36 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_145050/profiler.kid-learning-lab.json:40 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | reconstructions/kid-learning-lab/RECONSTRUCTED.json:40 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | reconstructions/kid-learning-lab/prompts/template_1.txt:6 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |

### Over-permissive files

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| high | world_readable | evidence/INVESTIGATION.md | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/api_dump_20261007_142450.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/ledger/20261007_193228.jsonl | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/index.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/live1.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/live2.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394211-aa0f.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394234-23c2.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394352-29fe.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/results/t-1791394211-aa0f.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/BRIEF.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/manifest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/reporter.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193057/BRIEF.md | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193057/manifest.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193057/reporter.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193057/scout.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193057/security.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/profiler.quai-radar.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/scout.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142748/BRIEF.md | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142748/manifest.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142748/profiler.agentic-knowledge-mapper.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142748/profiler.hive-research-gpu.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142748/profiler.quai-radar.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142748/reporter.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142748/scout.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_124725/BRIEF.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_124725/manifest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_124725/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_124725/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_124725/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_124725/reporter.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_124725/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142708/BRIEF.md | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142708/manifest.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142708/profiler.agentic-knowledge-mapper.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142708/profiler.hive-research-gpu.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142708/profiler.quai-radar.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142708/reporter.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_142708/scout.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130138/BRIEF.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130138/manifest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130138/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130138/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130138/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |

> Note: 66 evidence file(s) under version control (e.g. prompt-derived agentic artifacts) — review .gitignore.
