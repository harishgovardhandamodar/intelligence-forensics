# Intelligence Forensics — unified report

## Provenance

| field | value |
|---|---|
| generated | 2026-10-07 18:00:36 |
| host | intel-forensics (Linux-7.0.0-38-generic-x86_64-with-glibc2.41) |
| source DB | `/app/evidence/fox_services_20261007_193228.db` |
| DB SHA-256 | `dfc265a8e7fee2fa6156b0155157315385280cb9d17fcdc25cf8a338bbdc6209` |
| DB size | 12513280 bytes, mtime 2026-10-07 17:32:28 |
| model | qwen3.8:27b |
| agent run | 20261007_193228 |
| requests / services | 2720 / 8 |

## Changes since last run

_First run — no previous version to diff._

## Services

| service | project | reqs | tokens | score | grade |
|---|---|---|---|---|---|
| agentic-knowledge-mapper | multi-agent debate risk scorer | 1226 | 2200581 | 89.7 | A |
| quai-radar | blockchain-news knowledge-graph extractor | 1151 | 1803855 | 91.5 | A |
| hive-research-gpu | paper-surrogate / research-paper summarizer | 277 | 318817 | 84.8 | A |
| kid-learning-lab | tutor / learning-lab skill coach | 37 | 2363 | 74.2 | B |
| gateway-unknown | gateway-unknown workload (unclassified) | 21 | 161 | 39.5 | D |
| live-selftest | live-selftest workload (unclassified) | 6 | 299 | 51.3 | C |
| probe | probe workload (unclassified) | 1 | 0 | 28.4 | D |
| warmup | warmup workload (unclassified) | 1 | 0 | 28.4 | D |

## Security posture

Risk rating: **high** (620 findings; low=1, medium=305, high=314)

### Secret / PII survivors

- **low** private_ip — evidence/swarm/results/t-1791394211-aa0f.json:1 → Confirm the internal address is expected; avoid leaking topology in reports.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:46 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:47 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:48 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:49 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:50 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:51 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:52 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:53 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:54 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:55 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:56 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:57 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:58 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:59 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:60 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:61 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:62 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:63 → Verify whether this is a live secret; rotate if so.
- **high** high_entropy — evidence/agentic/20261007_174732/BRIEF.md:64 → Verify whether this is a live secret; rotate if so.

### Prompt-injection attempts

- **medium** prompt_injection:role_hijack — evidence/INVESTIGATION.md:88 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:100 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:101 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:102 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:103 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:104 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:105 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:106 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:107 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:108 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:109 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:110 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:111 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:112 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:113 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:114 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:115 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:116 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:117 → Keep fenced as untrusted data; never let prompts steer reconstruction.
- **medium** prompt_injection:role_hijack — evidence/agentic/20261007_174732/BRIEF.md:118 → Keep fenced as untrusted data; never let prompts steer reconstruction.

### Over-permissive files

- **high** world_readable — evidence/INVESTIGATION.md → chmod 0600 evidence files and set the collector umask to 077.
- **high** world_readable — evidence/api_dump_20261007_142450.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/ledger/20261007_174732.jsonl → chmod 0600 evidence files and set the collector umask to 077.
- **high** world_readable — evidence/ledger/20261007_193228.jsonl → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/ledger/index.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/ledger/live1.jsonl → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/ledger/live2.jsonl → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/swarm/queue/done/t-1791394211-aa0f.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/swarm/queue/done/t-1791394234-23c2.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/swarm/queue/done/t-1791394352-29fe.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/swarm/results/t-1791394211-aa0f.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/registry.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_130116/BRIEF.md → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_130116/manifest.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_130116/profiler.agentic-knowledge-mapper.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_130116/profiler.hive-research-gpu.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_130116/profiler.quai-radar.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_130116/reporter.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_130116/scout.json → chmod 0600 evidence files and set the collector umask to 077.
- **medium** world_readable — evidence/agentic/20261007_174732/BRIEF.md → chmod 0600 evidence files and set the collector umask to 077.

## Trust boundaries

| rule | status | severity | detail |
|---|---|---|---|
| T1 | pass | critical | Fox DB is opened read-only and never written. |
| T2 | warn | medium | Browser fallback loads an asset from a CDN host. |
| T3 | pass | critical | Inference targets local Ollama only; no cloud model host. |
| T4 | pass | critical | Container holds no tokens/keys and no Docker socket. |
| T5 | pass | medium | README documents no-auth LAN/tailnet exposure and bind. |
| T6 | pass | high | Every scaffold ships RECONSTRUCTED.json + caveats. |
| T7 | pass | high | Swarm workers run as host UID with least-privilege mounts. |
| T8 | pass | high | Destructive actions require a ledger-recorded human approval. |

_{'pass': 7, 'warn': 1, 'fail': 0}_

## Inflow risk by service

| service | band | score | prompts | PII | injections | reuse |
|---|---|---|---|---|---|---|
| kid-learning-lab | medium | 47.0 | 37 | 0 | 8 | 2 |
| agentic-knowledge-mapper | medium | 35.1 | 1226 | 0 | 42 | 0 |
| gateway-unknown | medium | 33.2 | 21 | 0 | 0 | 13 |
| hive-research-gpu | low | 19.9 | 277 | 0 | 0 | 0 |
| quai-radar | low | 19.3 | 1151 | 0 | 0 | 0 |
| probe | low | 3.2 | 1 | 0 | 0 | 0 |
| warmup | low | 3.2 | 1 | 0 | 0 | 0 |
| live-selftest | low | 3.1 | 6 | 0 | 0 | 0 |

## Agentic deep investigation

run `20261007_193228` model=qwen3.8:27b elapsed=17.0s agents_ok=2

### quai-radar
- heuristic: blockchain-news knowledge-graph extractor
- LLM: Quai Network Intelligence Dashboard & Knowledge Graph (confidence 0.95)
- agreement: partial

### Reporter brief

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
_Caveat: fox telemetry stores truncated, secret-redacted, PII-masked prompt heads; completions are not logged. Reconstructions recover templates and pipeline, not exact source._