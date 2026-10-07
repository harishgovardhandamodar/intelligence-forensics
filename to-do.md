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
