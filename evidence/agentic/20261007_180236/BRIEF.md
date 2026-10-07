# Agentic forensic brief
run: 20261007_180236 model: qwen3.8:27b
elapsed: 270.1s quick=False

## Executive Brief: LLM Mesh Architecture & Risk

**Overview**
The monitored mesh comprises eight distinct services ranging from high-confidence intelligence pipelines to low-confidence infrastructure probes. The architecture relies heavily on LLM extraction, summarization, and risk assessment capabilities.

### Node Capabilities
*   **quai-radar**: High-confidence (0.95) intelligence dashboard. Ingests news/market data, extracts structured facts into a knowledge graph, and generates daily research briefs.
*   **kid-learning-lab**: Adaptive tutoring engine (0.92). Uses dual-model approach (embeddings + LLM) to generate pedagogical prompts and tutor responses for children.
*   **agentic-knowledge-mapper**: Risk assessment engine (0.85). Evaluates security/operational risks of multi-agent systems, mapping CVEs and failure modes (e.g., prompt injection) to generate risk registers.
*   **hive-research-gpu**: Academic summarization service (0.95). Processes research papers (multi-agent/RL focus) to build knowledge surrogates and briefs.
*   **gateway-unknown**: Low-confidence (0.3) LLM proxy. Routes simple chat/readiness prompts to various models (Nomic, Qwen).
*   **live-selftest**: Diagnostic probe (0.4). Tests multi-agent debate capabilities and validates system behavior via risk briefs.
*   **probe**: Health-check service (0.2). Validates LLM connectivity and endpoint responsiveness.
*   **warmup**: Connection initializer (0.95). Triggers model loading using static prompts to ensure backend readiness.

### Shared Topics
*   **LLM Orchestration**: All nodes utilize LLM calls for core functions (extraction, generation, routing).
*   **Risk & Security**: `agentic-knowledge-mapper` and `live-selftest` explicitly focus on risk assessment and multi-agent security.
*   **Knowledge Structuring**: `quai-radar` and `hive-research-gpu` both convert unstructured text into structured knowledge graphs or surrogates.
*   **Infrastructure Validation**: `probe`, `warmup`, and `gateway-unknown` serve as foundational connectivity and readiness layers.

### Primary Reconstruction Target
**`agentic-knowledge-mapper`**
This node is the most valuable target for reconstruction. It provides the critical security layer for the entire mesh, specifically addressing multi-agent risks, CVE mapping, and prompt injection vulnerabilities. Its output (risk registers) directly informs the security posture of the other LLM-dependent nodes.

## Security Posture
**Risk Rating: HIGH**
*   **Evidence**: 781 high-severity issues, 1,237 medium-severity issues.
*   **Top Issues**:
    1.  **Prompt Injection Exposure**: Multiple nodes (`quai-radar`, `kid-learning-lab`) ingest untrusted external data (news, user inputs) directly into LLM prompts without visible sanitization.
    2.  **Unvalidated LLM Outputs**: `gateway-unknown` and `live-selftest` route outputs to "unknown sinks," creating potential data exfiltration or injection paths.
    3.  **Lack of Input Validation**: `kid-learning-lab` processes learner states and tasks without clear evidence of strict schema validation, risking manipulation of pedagogical outputs.
*   **Remediation**:
    1.  Implement strict input sanitization and prompt injection defenses for all ingestion pipelines.
    2.  Validate and sanitize all LLM outputs before they reach downstream sinks or users.
    3.  Enforce

---

# Security posture — HIGH

_generated 2026-10-07 18:07:07 · deterministic scan of evidence/reconstructions_

## Findings by severity

| severity | count |
|---|---|
| high | 781 |
| medium | 1237 |
| low | 1 |

## Deterministic detail

### Secret / PII survivors

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| low | private_ip | evidence/swarm/results/t-1791394211-aa0f.json:1 | 172.….1 | Confirm the internal address is expected; avoid leaking topology in reports. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:265 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:274 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:283 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:292 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:301 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:310 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:319 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:328 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:337 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:346 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:355 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:364 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:373 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:382 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:391 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:400 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:409 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:418 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:427 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:436 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:445 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:454 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:463 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:472 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:481 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:490 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:499 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:508 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:517 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:526 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:535 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:544 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:553 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:562 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:571 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:580 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:589 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:598 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:607 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:616 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:625 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:634 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:643 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:652 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:661 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:670 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:679 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:688 | evid…EF | Verify whether this is a live secret; rotate if so. |
| high | high_entropy | evidence/reports/20261007_180037/report.json:697 | evid…EF | Verify whether this is a live secret; rotate if so. |

### Prompt-injection attempts

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| medium | prompt_injection:role_hijack | evidence/INVESTIGATION.md:88 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2267 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2276 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2285 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2294 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2303 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2312 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2321 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2330 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2339 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2348 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2357 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2366 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2375 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2384 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2393 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2402 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2411 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2420 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2429 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2438 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2447 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2456 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2465 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2474 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2483 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2492 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2501 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2510 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2519 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2528 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2537 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2546 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2555 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2564 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2573 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2582 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2591 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2600 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2609 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2618 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2627 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2636 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2645 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2654 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2663 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2672 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2681 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2690 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |
| medium | prompt_injection:role_hijack | evidence/reports/20261007_180037/report.json:2699 | Act as | Keep fenced as untrusted data; never let prompts steer reconstruction. |

### Over-permissive files

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| high | world_readable | evidence/INVESTIGATION.md | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/api_dump_20261007_142450.json | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_174732.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_180225.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_180236.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_180243.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_180244.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_180245.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_180246.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/20261007_180319.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| high | world_readable | evidence/ledger/20261007_193228.jsonl | 0664 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/index.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/live1.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/ledger/live2.jsonl | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394211-aa0f.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394234-23c2.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/queue/done/t-1791394352-29fe.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/swarm/results/t-1791394211-aa0f.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/reports/index.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/reports/20261007_180037/report.html | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/reports/20261007_180037/report.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/reports/20261007_180037/report.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/registry.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/BRIEF.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/manifest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/reporter.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_130116/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.gateway-unknown.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.kid-learning-lab.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.live-selftest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.probe.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.warmup.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/BRIEF.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/manifest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/reporter.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_174732/security.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180319/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180319/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180319/profiler.kid-learning-lab.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
