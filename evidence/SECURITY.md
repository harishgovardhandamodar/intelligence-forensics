# Security posture — CRITICAL

_generated 2026-10-07 18:13:38 · deterministic scan of evidence/reconstructions_

## Summary

The LLM-gateway forensics environment exhibits critical security failures, including the exposure of 50 API routes without authentication and a mutating endpoint accessible via GET requests. Additionally, high-entropy data resembling secrets is present in report files, and numerous evidence files have overly permissive world-readable permissions. These issues collectively allow unauthorized access to sensitive forensic data and potential system manipulation.

## Findings by severity

| severity | count |
|---|---|
| high | 806 |
| medium | 1668 |
| low | 1 |

## Advisor findings

| severity | title | status | remediation |
|---|---|---|---|
| high | Unauthenticated API Access | open | Implement mandatory authentication and authorization checks for all API endpoints. |
| high | Mutating Endpoint via GET | open | Restrict mutating operations to POST/PUT/DELETE methods and enforce CSRF protection. |
| high | High Entropy Secrets in Reports | open | Redact or encrypt high-entropy values in report files and rotate any exposed credentials. |
| high | World-Readable Sensitive Files | open | Change file permissions to 0600 or 0640 to restrict access to owner/group only. |
| medium | Prompt Injection Attempts | open | Sanitize input data and implement prompt injection detection filters in the LLM gateway. |
| medium | Evidence Enumeration Exposure | open | Require authentication for evidence listing and download endpoints. |
| low | Private IP Exposure | open | Redact internal IP addresses from exported evidence files. |

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
| medium | world_readable | evidence/agentic/20261007_180245/BRIEF.md | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.gateway-unknown.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.kid-learning-lab.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.live-selftest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.probe.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/critic.warmup.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/manifest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.agentic-knowledge-mapper.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.gateway-unknown.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.hive-research-gpu.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.kid-learning-lab.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.live-selftest.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.probe.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.quai-radar.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/profiler.warmup.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/reporter.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |
| medium | world_readable | evidence/agentic/20261007_180245/scout.json | 0644 | chmod 0600 evidence files and set the collector umask to 077. |

### Dashboard exposure

| severity | kind | source | detail | remediation |
|---|---|---|---|---|
| high | side_effecting_get | /api/runs | mutating route also served over GET | Serve mutating actions over POST only. |
| high | no_auth | dashboard | 50 /api routes served without authentication | Put the dashboard behind authentication / bind it to loopback. |
| medium | evidence_enumeration | /api/evidence | evidence can be listed/downloaded without auth | Gate /api/evidence* behind authentication. |
