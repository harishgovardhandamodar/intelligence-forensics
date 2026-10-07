# Agentic forensic brief
run: 20261007_174732 model: qwen3.8:27b
elapsed: 25.2s quick=True

## Executive Brief: Mesh Service Analysis

**Node Capabilities**
*   **agentic-knowledge-mapper:** Constructs risk registers for LLM multi-agent debate architectures. Maps attack vectors (prompt injection, collusion) to exposure tiers and control measures.
*   **hive-research-gpu:** Processes academic papers in multi-agent systems and RL. Generates condensed "surrogates" and knowledge graph hints from abstracts and experimental setups.
*   **quai-radar:** Monitors Quai Network market dynamics. Extracts structured facts from external feeds to build knowledge graph nodes and daily research briefs.

**Shared Topics**
All three nodes converge on **multi-agent system analysis** and **knowledge graph construction**. The mapper defines the risk framework, the GPU node provides the academic substrate, and the radar ingests live market data to populate the graph.

## Security Posture
**Risk Rating:** **HIGH**
**Top Issues & Remediation:**
1.  **High-Severity Findings (154):** Immediate triage required for critical vulnerabilities. *Remediation:* Patch high-severity CVEs identified in the `map_attacks` pipeline.
2.  **Medium-Severity Backlog (146):** Significant exposure surface. *Remediation:* Prioritize remediation of medium-risk items to reduce attack surface.
3.  **Untracked Evidence (0):** Lack of forensic linkage. *Remediation:* Implement evidence tracking to correlate findings with specific service instances.

**Reconstruction Target**
The **agentic-knowledge-mapper** risk register is the single most valuable target. It synthesizes the academic insights from `hive-research-gpu` and market context from `quai-radar` into a structured control framework, providing the highest leverage for understanding the mesh’s operational security and failure modes.

---

# Security posture — HIGH

_generated 2026-10-07 17:47:57 · deterministic scan of evidence/reconstructions_

## Findings by severity

| severity | count |
|---|---|
| high | 154 |
| medium | 146 |
| low | 1 |

## Deterministic detail

### Secret / PII survivors

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| low | private_ip | evidence/swarm/results/t-1791394211-aa0f.json:1 | 172.….1 | Confirm the internal address is expected; avoid leaking topology in reports. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:51 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:52 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:53 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:54 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:55 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:56 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:57 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:75 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:76 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:77 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:78 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:79 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:80 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:81 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:82 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:83 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:84 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:85 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:86 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:87 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:88 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:89 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:134 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:141 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:148 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:155 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:162 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/BRIEF.md:169 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:17 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:26 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:35 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:44 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:53 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:62 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:71 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:190 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:199 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:208 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:217 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:226 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:235 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:244 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:253 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:262 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:271 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:280 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:289 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:298 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/agentic/20261007_193228/security.json:307 | evid…EF | Verify whether this is a live secret; rotate if so. |

### Prompt-injection attempts

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| medium | prompt_injection:role_hijack | evidence/INVESTIGATION.md:88 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:74 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:75 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:76 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:77 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:78 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:79 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:80 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:81 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:82 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:83 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:84 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:85 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:86 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:87 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:88 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:89 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:90 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:91 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:92 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:93 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:94 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:95 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:96 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:97 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:98 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:99 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:100 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:101 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:102 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:103 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:104 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:105 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:106 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:107 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:108 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:109 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:110 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:111 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:112 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:113 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:114 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:115 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:116 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:117 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/BRIEF.md:118 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/security.json:183 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/security.json:192 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/security.json:201 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/agentic/20261007_193228/security.json:210 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |

### Over-permissive files

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| high | world_readable | evidence/INVESTIGATION.md | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/api_dump_20261007_142450.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_174732.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/ledger/20261007_193228.jsonl | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/index.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/live1.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/live2.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394211-aa0f.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394234-23c2.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394352-29fe.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/results/t-1791394211-aa0f.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/registry.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/BRIEF.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/manifest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/reporter.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/BRIEF.md | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/manifest.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/profiler.quai-radar.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/reporter.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/scout.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/agentic/20261007_193228/security.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
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
