# Agentic forensic brief
run: 20261007_180243 model: qwen3.8:27b
elapsed: 345.3s quick=False

## Executive Brief: LLM Mesh Architecture & Risk Profile

**Overview**
The monitored mesh comprises a specialized LLM inference cluster focused on **agentic safety**, **educational tutoring**, and **blockchain intelligence**. The architecture relies on a shared gateway layer routing prompts to local models (Llama, Qwen, Gemma, Nomic).

### Node Functions
*   **agentic-knowledge-mapper**: Core safety engine. Maps LLM failure modes (sycophancy, injection) to risk registers. *Confidence: 0.85*
*   **kid-learning-lab**: Pedagogical adapter. Generates non-directive tutoring prompts for learners. *Confidence: 0.95*
*   **quai-radar**: Intelligence dashboard. Extracts structured facts from news/market data into a knowledge graph. *Confidence: 0.95*
*   **hive-research-gpu**: Academic processor. Summarizes multi-agent/RL papers into surrogates. *Confidence: 0.85*
*   **Infrastructure (gateway-unknown, probe, warmup, live-selftest)**: Low-confidence routing, health checks, and self-testing loops. *Confidence: 0.3–0.85*

### Shared Topics
1.  **Multi-Agent Systems**: Central to `agentic-knowledge-mapper` (risk assessment) and `hive-research-gpu` (paper analysis).
2.  **Prompt Engineering**: All nodes rely on structured prompt pipelines (`make_brief`, `learner_state_ingestion`, `build_kg_prompt`).
3.  **Local Model Orchestration**: Heavy reliance on local inference (Llama 3.2, Qwen 3.8, Gemma 4) via a shared gateway.

### Primary Reconstruction Target
**`agentic-knowledge-mapper`**
*   **Rationale**: It is the only node explicitly generating **control recommendations** and **attack mappings**. Reconstructing its logic provides the highest value for understanding the mesh’s defensive posture and how it mitigates prompt injection across other services.

## Security Posture
**Risk Rating: HIGH**
*   **Metrics**: 787 High-severity findings; 1,327 Medium-severity findings.
*   **Top Issues**:
    1.  **Untrusted Input Handling**: `quai-radar` ingests external news feeds; `kid-learning-lab` processes user state. Both are vulnerable to prompt injection if sanitization is insufficient.
    2.  **Gateway Opacity**: `gateway-unknown` and `probe` have low confidence (0.3) and undefined sinks, creating potential blind spots for traffic interception or model poisoning.
    3.  **Self-Testing Loops**: `live-selftest` generates risk briefs but lacks clear output validation, potentially allowing malicious test cases to persist.
*   **Remediation**:
    1.  Implement strict input sanitization and output validation for `quai-radar` and `kid-learning-lab`.
    2.  Audit `gateway-unknown` routing logic to ensure no unauthorized model access or data exfiltration.
    3.  Integrate `agentic-knowledge-mapper`’s risk registers into the CI/CD pipeline to automatically flag high-risk prompt patterns.

---

# Security posture — HIGH

_generated 2026-10-07 18:08:29 · deterministic scan of evidence/reconstructions_

## Findings by severity

| severity | count |
|---|---|
| high | 787 |
| medium | 1327 |
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
| medium | world_readable | evidence/agentic/20261007_180245/critic.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.kid-learning-lab.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
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
