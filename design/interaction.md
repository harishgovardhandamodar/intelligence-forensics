# 03 — Interaction

What calls what, in what order, on every major flow. Three flows matter:
heuristic investigation, agentic run, and serving. All reads; the only write
targets are our own `evidence/` and `reconstructions/` directories.

Related: [02-uml.md](02-uml.md) · [activity.md](activity.md) ·
[data-model.md](data-model.md)

## Flow 1: heuristic investigation (`investigate` + `build`)

```mermaid
sequenceDiagram
    participant OP as operator / dashboard
    participant FX as fox_client + store
    participant FOX as fox-services :8210
    participant DB as fox_services.db copy
    participant INF as infer + score
    participant FS as evidence/ + reconstructions/
    OP->>FX: snapshot_api(hours, req_limit)
    FX->>FOX: GET /api/stats, /llm/*, /mesh/* …
    FOX-->>FX: JSON dumps
    FX->>FS: api_dump_{stamp}.json
    OP->>FX: snapshot_db()
    FX->>DB: cp fox_services.db (WAL-safe)
    OP->>INF: investigate_all(rows)
    INF-->>OP: profiles {project, pipeline, models…}
    OP->>INF: progression + score per step
    INF-->>OP: steps + deltas + converged
    OP->>FS: INVESTIGATION.md + scaffolds
```

## Flow 2: agentic run (`agent-run`, full mode)

```mermaid
sequenceDiagram
    participant OP as operator / dashboard
    participant SC as scout
    participant PR as profilers (×N, threaded)
    participant CR as critics (×N, threaded)
    participant RP as reporter
    participant OL as Ollama qwen3.8:27b
    participant FS as evidence/agentic/{run_id}/
    OP->>SC: rank services from traffic summary
    SC->>OL: ask_json (≤512 tok)
    OL-->>SC: rankings
    SC-->>FS: scout.json
    OP->>PR: profile each service (≤768 tok)
    PR->>OL: ask_json ×N in parallel
    OL-->>PR: {project, pipeline, confidence…}
    PR-->>FS: profiler.{svc}.json
    OP->>CR: review each profile (≤256 tok)
    CR->>OL: ask ×N in parallel
    OL-->>CR: gaps list
    CR-->>FS: critic.{svc}.json
    OP->>RP: brief from all profilers
    RP->>OL: ask
    OL-->>RP: markdown brief
    RP-->>FS: reporter.json + BRIEF.md + manifest.json
```

Quick mode skips the critic stage and profiles only the top-3 services.
Dashboard launches run the same function on a background thread and poll
`background_status` — the HTTP request never blocks on the model.

## Flow 3: serving (dashboard + Design tab)

```mermaid
sequenceDiagram
    participant BR as browser (LAN/tailnet)
    participant D as dashboard.py
    participant DD as design_docs.py
    participant FOX as fox-services :8210
    BR->>D: GET /api/services
    D->>D: _service_rows (newest evidence DB)
    D-->>BR: profiles + scores + vibe
    BR->>D: GET /api/design/docs/uml
    DD->>DD: fixed-index lookup (else 404)
    DD-->>BR: markdown
    BR->>BR: render md + lazy mermaid.js (CDN, fallback: source)
    BR->>D: GET /api/fox/live
    D->>FOX: stats + mesh + queue (best effort)
    FOX-->>D: JSON or _error
    D-->>BR: live panel (never wedges page)
```
