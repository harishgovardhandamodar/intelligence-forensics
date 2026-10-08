# to-do.md — gap analysis & improvement plan

Findings from the audit of live forensic collection, mapping, reconstruction,
charts/GUI, reporting, and the missing security advisor agent. Work proceeds
P0 → P4, one commit per stage.

---

## A. Live collection · mapping · reconstruction (LLM in/out flow)

**Core gap: there is no *outflow*.** `README.md:148` admits completions are
never logged, and `iforensics/live.py` only ever sees fox's own view — truncated
prompt heads in, token counts out. Everything downstream (`progression.py`,
`score.py`, `reconstruct.py`) reconstructs a *half-duplex* signal: request shape
can be fingerprinted, but inferred I/O schema can never be validated, output
never diffed, prompt drift at the response end never detected.

| # | Gap | Evidence |
|---|---|---|
| A1 | **Silent event loss.** `req_limit=100` per 5s poll — if >100 requests complete in one interval the oldest are never fetched, never counted, never reported. No `dropped` counter exists. | `live.py:44`, `live.py:92-101` |
| A2 | **No IN→OUT correlation.** Queue and completion events both carry `qid` but are never joined, so queue-wait, abandonment and drop rate are unmeasurable. `store.py:57` already selects `queue_ms` — the tap ignores it. | `live.py:104-116` |
| A3 | **Live state is volatile.** `events` is a process-local `deque(maxlen=2000)`; restart the dashboard and the forensic window is gone. For a forensics tool, losing evidence on restart is a chain-of-custody failure. | `live.py:48` |
| A4 | **Unbounded memory.** `seen_ids` / `seen_inflight` grow forever, never pruned. | `live.py:49-50` |
| A5 | **No topology mapping.** Mesh peers, docker projects and LLM traffic are read in three places and never joined. No service → container → peer → model graph exists. | `fox_client.py:72-89` |
| A6 | **Poll-only delivery.** Dashboard re-fetches feed + rates + services every 4s as full JSON. No SSE, no `since_id` cursor, no delta. | `dashboard.py:301` |
| A7 | **No staleness alarm.** `last_poll_at` is recorded but never checked — a hung fox shows a green "live" with frozen data. | `live.py:138`, `dashboard.py:276` |
| A8 | **pcap is a dead end.** Sidecar writes raw packets and nothing parses them — the highest-fidelity evidence source is unreadable by the app. | `docker-compose.yml` pcap profile |
| A9 | **Row-shape divergence.** Live rows use `chosen_model or model` + computed `total_tokens` (`live.py:29`, `live.py:79`); history rows use `model` + DB column (`live.py:186-189`). Mixed rows shift `model_focus` in `score.py:35`. `requestor` hardcoded `"user"` in live rows. | `live.py:82` |
| A10 | **No anomaly detection.** No spike/error/new-service/model-eviction alerts; SYS events logged but never acted on. | — |
| A11 | **Concurrency nit.** `status()` iterates `self.events` outside the lock (`live.py:166`) while the tap appends → `deque mutated during iteration` possible. | `live.py:166` |
| A12 | **Single global tap.** One module-global `_TAP`, no per-service scoping, breaks under >1 uvicorn worker. | `live.py:199` |

---

## B. Charts & GUI

`dashboard.py` is 645 lines with a 275-line HTML/JS string inline (`PAGE`,
L30-306). Two hand-rolled SVG charts total.

1. **Only two charts exist** — score curve + agent DAG. No traffic timeline,
   token-volume area, latency distribution, model-mix breakdown, per-service
   heatmap or Overview sparkline. Rates are a static table.
2. **No time-series API.** No `/api/stats/timeseries`, nothing buckets
   per-minute counts — "req/min over 24h" is not renderable today.
3. **Chart quality:** no axis titles, no legend, no hover tooltip framework
   (SVG `<title>` only), fixed `viewBox`, no resize/zoom/brush, hardcoded
   0/25/50/75/100 gridlines regardless of data range (`dashboard.py:164`).
4. **Stored XSS rendering foreign data.** `escH()` is used *only* inside
   `renderMarkdown` — **zero** `innerHTML` assignments escape. Prompt heads,
   `what_building`, `evidence_quotes`, critic gaps, service and model names are
   interpolated raw (`dashboard.py:124`, `:179-204`, `:279`). Prompt heads come
   from *other services'* traffic and the dashboard has no auth — cross-service
   injection into every viewer.
5. **Path-traversal prefix check wrong:** `target.startswith(base)` at
   `dashboard.py:437` — a sibling dir named `<base>x` passes. Needs
   `base + os.sep`.
6. **Side-effecting GET:** `/api/investigate` (`dashboard.py:379`) collects and
   *writes a file* on GET — prefetchers will trigger it.
7. **No caching:** `_service_rows()` → `load_requests` → `infer.investigate_all`
   over 5000 rows re-runs on every `/api/services` poll, every 4s.
8. **UX gaps:** tabs not in the URL, tables not sortable/filterable/searchable,
   no loading/empty/error state convention (`sec()` defined then used once,
   `dashboard.py:116`), no CSV/JSON export, Evidence tab is a bare filename
   list with no preview/download, brief rendered as raw `<pre>`, no print/PDF
   view, hard-coded dark theme, no a11y attributes.
9. **No test/build surface:** 275 lines of JS inside a Python string cannot be
   linted, split or hot-reloaded.

---

## C. Reporting

1. **Two disconnected narratives.** `report.render` (`report.py:13`) produces
   `INVESTIGATION.md` from heuristics only — never reads agentic results,
   scores, vibe, progression, live rates. `BRIEF.md` (`agents.py:209-214`) is
   raw LLM output. Nothing merges them.
2. **No scores in the report.** `score.py` produces explainable 0-100 scores
   with per-factor breakdowns — and the report has no score table, no grade
   column, no evidence-strength ranking.
3. **Critic findings orphaned.** `critic.<svc>.json` gaps are shown in the
   dashboard but never merged into the brief or `INVESTIGATION.md`.
4. **No provenance block.** A forensic report should carry tool version,
   collection timestamp, source DB path + SHA-256, row counts, reachability,
   operator, config snapshot. Currently one caveat line (`report.py:52`).
5. **No history/diff.** `INVESTIGATION.md` overwritten every run
   (`dashboard.py:390`); no versioning, no "what changed since last run".
6. **No charts, no HTML/PDF export.** Markdown only.
7. **Reporter output unvalidated.** No schema check, no claims-vs-evidence
   separation, no "N of M claims unproven" completeness metric.
8. **No scheduled reporting.** Click-to-run only.

---

## D. Security advisor agent (missing entirely)

Agent roster is `scout → profiler → critic → reporter` (`agents.py:5`) — **no
security role**, and `design/trust-boundaries.md` labels T1–T6 "enforced, not
advised" with nothing verifying them.

| # | Gap | Detail |
|---|---|---|
| D1 | **Prompt injection into the reconstruction pipeline.** | `_compact_profile` (`agents.py:52`) embeds *foreign services'* prompt text directly into the profiler's LLM context; `ask_json` (`ollama_client.py:60`) has no untrusted-data fencing. A service can craft a prompt head that steers the reconstruction of itself or a neighbour. Same for `evidence_quotes` and `critic_gaps` re-rendered in the UI. Needs delimiter fencing + "data, not instructions" rules *and* an injection-pattern scanner. |
| D2 | **Evidence leak scanner.** | Regex/entropy scan of `evidence/`, `reconstructions/`, `INVESTIGATION.md`, `evidence/agentic/*` for key/token/IP/email/health survivors. Concrete current findings: `api_dump_*.json` is `0644` while DB copies are `0600`; 59 files under `evidence/agentic/` are **git-tracked** with `evidence_quotes` derived from prompts. |
| D3 | **Dashboard/exposure audit.** | No-auth reality vs T5, `0.0.0.0` bind, side-effecting GET, `startswith` prefix bug, missing output escaping, unauthenticated POST `/api/runs` (LAN fork-bomb of Ollama), unauthenticated `/api/evidence` enumeration. |
| D4 | **Trust-boundary conformance.** | Parse T1–T6 from `design/trust-boundaries.md` and assert against code/config each run: ro mount present? peer IPs in source? cloud base URL? `.gitignore` covering pcaps? Turns the design tab from prose into a test suite. |
| D5 | **Per-service risk scoring over inflow.** | Which services send PII-shaped content, jailbreak/agent-escape phrasing, anomalous token volumes, or near-identical templates to each other (cross-service prompt leakage). Security complement to the vibe index. |
| D6 | **Output surface.** | Structured `security.json` per run + `evidence/SECURITY.md` + `/api/security` + **Security** dashboard tab (severity / evidence / remediation / status), folded into the reporter so the exec brief carries a risk section. |

Implementation follows the house pattern: a **deterministic pre-scan that runs
without the LLM** (works when Ollama is down — same heuristic-vs-LLM split used
elsewhere) feeding an LLM advisor role for interpretation, artifacts under
`evidence/agentic/<run>/security.json`.

---

## E. Cross-cutting

- **Zero tests.** No `tests/`, no pytest config, no CI. `score.py`,
  `progression.py`, `infer.py`, `fingerprints.py` are pure functions — the
  easiest and highest-value targets, and they encode the tool's entire
  explanatory claim.
- **22 bare `except Exception`**, ~10 `pass`-only in `live.py` alone.
- **No structured logging** — `print()` in CLI, nothing in the server.
- **No pinning:** `requirements.txt` is 3 unpinned lines; README depends on a
  *sibling repo's* venv (`/home/fox/codebase/.venv`).
- **Evidence retention:** 10 × 12.5 MB DB snapshots, two taken 2 seconds
  apart, no pruning policy.
- **Module globals** (`_TAP`, `_RUNS`, `_LOCK`) don't survive multi-worker
  uvicorn or restart.
- **No rate limiting** on any POST.

---

## Priorities

### P0 — correctness & safety (small, first)
- [x] P0.1 Escape all `innerHTML` interpolation (shared `escH` + `t()` helper)
- [x] P0.2 Fix `startswith` → `base + os.sep`; make `/api/investigate` a POST
- [x] P0.3 Report `dropped` counter; prune `seen_ids`; lock `status()` read
- [x] P0.4 Add `tests/` for `score.py` + `progression.py` + `fingerprints.py`

### P1 — live forensics depth
- [x] P1.5 Persist the tap to append-only `evidence/live/events-<day>.jsonl` + on-disk cursor
- [x] P1.6 Join IN→OUT on `qid`, surface `queue_ms`, `since_id` delta endpoint + SSE
- [x] P1.7 `/api/stats/timeseries?bucket=1m` endpoint
- [x] P1.8 Unify live/history row shapes (`model`, `total_tokens`, real `requestor`)

### P2 — charts & GUI
- [x] P2.9 Extract `static/app.css` + `static/app.js`; loading/empty/error states; URL-addressable tabs
- [x] P2.10 Traffic timeline, token volume, latency p50/p95, model mix, heatmap, sparklines; shared tooltip/legend/resize
- [x] P2.11 Sortable/filterable tables, CSV/JSON export, evidence preview + download, rendered markdown brief, print stylesheet

### P3 — security advisor agent
- [x] P3.12 Deterministic leak + exposure scanner (D2, D3)
- [x] P3.13 Untrusted-data fencing in `ollama_client.ask*` + injection scanner (D1)
- [x] P3.14 `SECURITY_SYSTEM` agent role + artifacts + Security tab + reporter integration (D6)
- [x] P3.15 Trust-boundary assertions (D4) + per-service risk score (D5)

### P4 — reporting
- [x] P4.16 Unified report generator: heuristic + agentic + scores + critic gaps + security findings, provenance block, SHA-256 of source DB
- [x] P4.17 Versioned reports + "changes since last run" diff; HTML export; scheduled runs

### Verification
- [x] Run the full test suite, boot the dashboard, smoke-test every API
      surface, commit each stage.

### P5 — remaining gaps (2026-10-07 verification; to-do §§A–E otherwise hold)
- [x] P5.18 Live anomaly alerts: error-rate spike, new-service, model load/evict,
      volume spike, stale edge — evaluated in the tap, surfaced in `status()` + Live tab
- [x] P5.19 Topology join: service→container→peer→model graph from already-collected sources
- [x] P5.20 Fidelity scoring: template recall of reconstructions vs observed traffic
      (`fidelity.py`, endpoint, CLI); full outflow still needs fox-side completions
- [x] P5.21 Reporter claims-vs-evidence validation + mermaid errors surfaced
- [x] P5.22 Retention/prune policy, pinned requirements, rate-limit POSTs, JS tests

### P6 — forensics UX: findings, timeline, knowledge graph, modern GUI
- [x] P6.23 Findings hub: severity-ranked list across security/risk/trust/claims/
      fidelity/alerts (`findings.py`, `/api/findings`, Findings tab)
- [x] P6.24 Chain of events: chronological IN→OUT lane linked by qid
      (`chain.py`, `/api/chain`, Timeline tab)
- [x] P6.25 Knowledge graph: services/templates/models/findings/evidence entities
      (`knowledge.py`, `/api/knowledge`, Graph tab)
- [x] P6.26 GUI modernization: light/dark theme toggle, sticky chrome, severity
      pills, timeline styles, loading shimmer, responsive breakpoints

### P7 — agent swarm with auditable ledger
- [x] P7.27 Ledger module: append-only hash-chained JSONL per run, verify,
      tail (`ledger.py` + tamper-detection tests)
- [x] P7.28 Instrument the existing run: every stage emits issued/completed
      entries with artifact hashes (no behavior change)
- [x] P7.29 Gatherers as tasks: fox/db/tap/mesh sources with per-source
      timeouts and retries
- [x] P7.30 Worker pool + disk-backed run registry (replace `_RUNS` global);
      crash recovery by replaying uncompleted tasks
- [x] P7.31 Surface: `/api/swarm/ledger` + Ledger tab, `ledger verify` CLI,
      human-approval entries for prune/export
- [x] P7.32 Agent isolation: one container per swarm role with NVIDIA GPU
      passthrough (2x RTX 5080 on axiom); file task queue under
      evidence/swarm; role-scoped mounts (gatherers get fox-data:ro,
      profilers get evidence only); fcntl-locked ledger appends
- [x] P7.33 Orchestrator dispatches profile/critic tasks to the swarm queue
      end-to-end (`swarm=True` mode: enqueue, container workers execute,
      orchestrator collects with timeout and carries on)
- [x] P7.34 Findings→ledger deep links (claims findings cite the run;
      Ledger tab preselects run/task from findings clicks)
- [x] P7.35 Live multi-worker verification: GPU passthrough proof, container
      profiler + full swarm agent-run against live fox/Ollama; worker
      `user:` directive (root-owned shared-volume files broke host writes)
- [x] P7.36 Ledger task-level filtering (client-side task/actor/action filter)
- [x] P7.37 Alert webhooks: `IF_ALERT_WEBHOOK` POST on every raised alert,
      delivery status in tap `status()`
- [x] P7.38 Run pile-up fixes (from live incident): in-flight runs visible
      first in `/api/runs` with elapsed spinner; `MAX_BACKGROUND_RUNS=2`
      with 429 + human message; unique run dirs/keys; defensive registry
      reads; `user:` on the main service (root-owned volume files broke
      host reads the same way workers did)
- [x] P7.31 Surface: `/api/swarm/ledger` + Ledger tab, `ledger verify` CLI,
      human-approval entries for prune/export

### P8 — embedding-reconstruction simulation (server in-app, sim/ client)
- [x] P8.1 Engine `iforensics/sim/`: synthetic sensitive data, progressive
      query generator, hash-embedding backend (+optional sentence-transformers),
      numpy vector store (+optional Milvus), mock gateway, reconstruction
      attacks (progressive, near-dup, membership), accuracy analysis
- [x] P8.2 Server: `/api/sim/*` (ingest/run-attack/report/reset) + Sim tab
      with progression chart
- [x] P8.3 Client `sim/`: 4 scenarios, runner CLI, settings.yaml (stdlib only)
- [x] P8.4 Compose `milvus` profile, docs, tests, verify

### P9 — workspace-wide security scan (parent folder, all subfolders)
- [x] P9.1 Workspace scope: allowlisted `app|workspace` roots (never raw paths)
- [x] P9.2 Triage: fixture flags, permission scoping, world-readable-secret
      escalation, per-project rollup, scope-aware report + persist
- [x] P9.3 Security tab: scope select, projects table, finding flags

### P10 — sim hardening: DLP, swarm reconstruction, estimation, styles
- [x] P10.1 Active DLP (off/audit/redact/block) with interception journal
- [x] P10.2 Swarm `sim_reconstruct` tasks via GPU containers + ledger trail
- [x] P10.3 Ground-truth-free leakage estimator + coding styles
      (one-off/regular/vibe) + plausibility assessment

### P11 — sim trigger + scenario diagrams in tab
- [x] P11.1 Server-side runner (`sim/runner.py`, shared report builder)
- [x] P11.2 `/api/sim/run` trigger + `/api/sim/scenarios` catalogue
- [x] P11.3 Sim tab run controls + per-scenario mermaid diagrams

### P12 — enterprise day-to-day workflow scenarios
- [x] P12.1 Synthetic generators (names, 555-phones, example.com mail,
      TEST routing, ghp_test tokens, .invalid webhooks — reserved space only)
- [x] P12.2 Six scenarios: hr_onboarding, support_tickets, devops_deploy,
      legal_contracts, sales_crm, data_engineering (+ runner/META, client,
      tab select, settings)
- [x] P12.3 Fixes found live: carrier-only paraphrase, known-wins assembly,
      span charsets (_ +/=), RFC-reserved TLD exemption in T2

### P13 — AKM-style agentic runs sub-tabs (gui-akm branch)
- [x] P13.1 Collected intel / Agent logs / Findings / Scores / Security verdict
      sub-tabs over one investigation (manifest + graph + validation)

### P14 — reconstruction simulation: stateless-inference residuals
- [x] P14.1 Engine `iforensics/sim/reconstruction.py`: eight surfaces as
      retention policies (6 stores + 1 linker + 1 analysis), three scenarios,
      deterministic hash-based sample rates, secret always at the end of long
      carriers, six reveal steps so per-surface accuracy spreads
- [x] P14.2 Server `/api/recon/*` (own namespace, own state, own rate limits)
      + Sim tab *Reconstruction* card with surface bars, cumulative curve,
      amplification delta and a raw residual inspector
- [x] P14.3 Client `recon_client/` (stdlib): terminal CLI + local web UI on
      `:8311`, peer address in `settings.yaml` so no `.py` names a
      non-loopback host (trust rule T2 stays green)
- [x] P14.4 `design/08-reconstruction-simulation.md` (11 diagrams incl. every
      surface's retention policy), registered in the fixed doc index;
      README section; `tests/test_reconstruction.py` (17 tests)

### P15 — reconstructions, harvest/attack collection, Fox-first Ollama
- [x] P15.1 **Stateless recon** sidebar tab: the whole P14 panel moved out of
      Sim into its own tab (scenario/seed controls, 7 KPIs, surface grid,
      cumulative + repetition charts, residual inspector, persisted-run picker)
- [x] P15.2 Reconstructions tab shows *both* halves of reconstruction — the
      modelled `reconstructions/stateless-inference/` service dir beside the
      six real ones, and every persisted `recon-*` run merged into
      `GET /api/reconstructions` (`kind: stateless-residual`), with
      `{svc}` / `{svc}/file` routed to `recon.load_run()`
- [x] P15.3 `iforensics/sim/harvest.py` — `recon_residuals` collection,
      strategy `harvest-now-consume-later`: every text-bearing residual is
      embedded on **ingest** (no ground truth needed) and attacked only on
      `POST /api/recon/consume`; `purge`/`reset` clear it, so a replayed
      session never double-harvests. Default backend is numpy; `MILVUS_URL`
      switches the same collection to Milvus
- [x] P15.4 Fox-first Ollama: `fox_client.ollama_running()` asks Fox
      `/api/ollama/running` first and falls back to a direct `:11434`
      `/api/ps`; both `live.py` poll sites use it; `/api/ollama` reports
      `via: fox|direct|none`
- [x] P15.5 `tests/test_recon_collections.py` (13 tests) — suite at 226

### P16 — modular insider-recon framework (`iforensics/sim/recon/`)
Plan: `to-do-insider-recon-instructions.md` (all 8 phases + repo mapping).
- [x] P16.0 Package skeleton; `core/secrets.py` (reserved-range validators +
      TruthRegistry over `sensitive.py`); `core/retention.py` (engine
      constants re-exported, never copied); `core/surfaces/base.py`
      (Turn/Residual/SurfacePolicy/EngineSurface)
- [x] P16.1 Seven engine-backed surface modules (policy card + live reader);
      eleven staged policy modules with deterministic `retain()` + store
- [x] P16.2 `core/{assembly,linkage,amplify,metrics}.py` over the engine
      (unscored candidates without truth; monotone-checked cumulative)
- [x] P16.3 Nine scenario adapters (3 engine-mapped + 6 generic-builder over
      engine primitives); `attacks/{progressive,near_dup,membership}.py`
- [x] P16.4 `api/routes.py` catalogue of all 15 `/api/recon/*` routes;
      stdlib CLI `client/run.py` (transport only); `ledger/chain.py` wrapper
- [x] P16.5 `mitigations.py` (caps, never-log-full, DLP off/audit/redact/
      block, cache TTL, embedding encryption-at-rest + sweep);
      `docs/{surfaces,honesty,ethics_gates}.md`; package README
- [x] P16.6 Framework test mirror (20 tests) + full suite green (253 total);
      CLI verified live against the dashboard, ledger verifies cleanly
