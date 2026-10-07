# Intelligence Forensics — investigator + builder

Reconstructs **what other nodes/services are building** purely by observing
`../fox-services` logs (LLM gateway telemetry, mesh peers, docker overview).

No access to their repos needed. The fox DB stores per-request
`service, model, prompt(head), query_type, requestor, tokens, timings` —
enough to fingerprint prompt templates, infer pipelines, and rebuild a
runnable scaffold of each observed codebase.

## Quick start

```bash
python cli.py investigate --hours 720 --limit 5000   # collect + profile + evidence/INVESTIGATION.md
python cli.py build                                    # reconstructions/<service>/ scaffolds
python cli.py build --only quai-radar
python cli.py fingerprint --service quai-radar
# LLM agentic deep-dive (local Qwen 3.8-27B via Ollama):
python cli.py agent-run --quick                        # top-3 services, ~20s
python cli.py agent-run                                # all services + critic stage, ~2-4 min
# Dashboard (FastAPI, needs repo venv for fastapi/uvicorn):
/home/fox/codebase/.venv/bin/python dashboard.py --port 8211   # open http://localhost:8211/
python cli.py dashboard --port 8211                    # same, via venv python
```

Env: `FOX_URL` (default `http://localhost:8210`), `FOX_SERVICES_DB` override,
`OLLAMA_URL` (default `http://localhost:11434`), `IF_MODEL` (default `qwen3.8:27b`),
`IF_PORT` (default `8211`).

## Docker + remote access (Tailscale / LAN)

```bash
docker compose up -d --build   # dashboard at :8211 (container `intel-forensics`)
```

The port binds `0.0.0.0:8211` (same mechanism as fox-services `:8210`), so it
is reachable off-host with no extra config:

- Tailscale: `http://100.101.3.115:8211` (this host = `axiom`)
- LAN: `http://192.168.1.173:8211`

From any other tailnet/LAN device: `curl http://100.101.3.115:8211/health`
should return `{"status":"ok",...}`. If it times out, host `ufw` is filtering
inbound — one fix: `sudo ufw allow 8211/tcp`. HTTPS alternative:
`sudo tailscale set --operator=$USER` once, then
`tailscale serve --bg http://127.0.0.1:8211` (tailnet-only
`https://axiom.<tailnet>.ts.net`, no firewall ports involved).

## How it works

1. **Collect** (`iforensics/fox_client.py`, `store.py`): dumps every fox API
   surface (stats, queue, mesh, docker, router) to `evidence/api_dump_*.json`
   and copies the SQLite DB (WAL-safe) to `evidence/fox_services_*.db`.
2. **Fingerprint** (`fingerprints.py`): clusters prompts per service into
   stable templates (slot-ify TITLE/CONTENT/Brief/Product/Subject/…),
   recovers instruction sentences + schema hints.
3. **Investigate** (`infer.py`): heuristic rules map template vocabulary to
   project labels + pipeline stages, with counts as evidence.
4. **Build** (`reconstruct.py`): emits `reconstructions/<service>/` with
   `inferred_pipeline.py` (runnable scaffold via fox gateway),
   `prompts/template_N.txt` (recovered templates), `RECONSTRUCTED.json`.
5. **Report** (`report.py`): `evidence/INVESTIGATION.md`.
6. **Agentic deep-dive** (`agents.py`, `ollama_client.py`): every agent is the
   local `qwen3.8:27b` (Ollama, `think:false` for speed) with a different role —
   `scout` ranks targets → `profiler` (per service, threaded) infers the build
   as JSON → `critic` lists what logs can't prove → `reporter` writes the exec
   brief. Artifacts per run: `evidence/agentic/<run_id>/{manifest,scout,
   profiler.*,critic.*,reporter,BRIEF.md}.json`.
7. **Dashboard** (`dashboard.py`): single-page UI — Overview, Services,
   Reconstructions (file browser + partial/progressive view + score chart),
   Agentic runs (graph, costs, agreement, gaps, trend), Mesh, Evidence,
   **Design** — plus one-click re-investigate and background agentic launches.

## Design & architecture tab

Like fox-services' own design tab: `design/*.md` (context, UML, interaction,
activity, data model, trust boundaries, privacy, ethics) rendered with live
Mermaid diagrams — 8 documents, 15 diagrams. Served via fixed-index API
(`GET /api/design/docs`, `GET /api/design/docs/{id}`; traversal attempts 404).
Mermaid v10 is vendored (`static/mermaid.min.js` → `/static/`, CDN fallback)
with a dark theme, so diagrams render even on offline LAN/tailnet; Markdown
gets proper joined paragraphs, lists, tables and code blocks in styled frames.

## Live sniffing (tap + optional pcap)

- **API-level tap** (no root): `iforensics/live.py` attaches to fox `:8210`
  and streams what goes in/out — queue first-seen (IN), completed requests by
  id delta (OUT), Ollama VRAM load/unload (SYS) — into a rolling buffer with
  per-service rates. Dashboard **Live tap** tab (start/stop, feed, rates,
  live reconstruction over traffic since tap started), or terminal:
  `python cli.py live-tail [--service X]`. Verified: a 5-probe burst scored
  D→C live as queries arrived.
- **Port-level pcap** (raw packets): `docker compose --profile pcap up -d
  pcap-tap` runs a `NET_RAW` tcpdump sidecar (host net, `tcp port 8210 or
  11434`, 10-min rotating files under `evidence/pcaps/`). Verified capturing
  real gateway traffic. WARNING: pcaps hold RAW unmasked prompts —
  gitignored, never commit, stop when done (`docker stop intel-pcap-tap`).

## Partial & progressive reconstructions
A full reconstruction uses every query at once. The Reconstructions tab can
instead re-profile one service's Fox queries slice-by-slice (oldest-first,
equal-count chunks) — no LLM needed, heuristic and instant:

```bash
python cli.py progression --service quai-radar --n 5 --mode cumulative  # confidence growth
python cli.py progression --service hive-research-gpu --n 4 --mode window  # per-slice partials
```

- `cumulative`: step k sees queries `0..k` — shows after how few queries the
  inferred build stabilizes (quai-radar: stable from step 1/229 queries).
- `window`: step k sees only its own slice — surfaces drift/instability
  (hive-research-gpu slices flip labels: per-slice vocabulary varies).
- API: `GET /api/reconstructions/{svc}/progression?n=5&mode=cumulative|window`
  with per-step Δ vs previous (label flip, new pipeline stages, template growth)
  and a `converged` flag.

## Scores & vibe index (`iforensics/score.py`)

Every profile and every progression step carries two transparent 0–100 scores
(formula in the module docstring, factors exposed per step):

- **Reconstruction score** (grade A/B/C/D): volume + template richness +
  instruction signal + schema clarity + model focus + label stability.
  Small apps climb visibly: kid-learning-lab goes 58.2 (C) → 73.6 (B) →
  86.2 (A) as queries accumulate; noise (`probe`) sits at ~28 (D).
- **Vibe index**: how much the app looks like a *pure vibe-coded* thin prompt
  wrapper (high query-per-template reuse, one model, few stages, prose-driven
  spec) vs an engineered system. quai-radar scores 80.3 "pure vibe" — an
  honest description of a single-prompt KG extractor — while thin/noisy
  services land "hybrid".

The Reconstructions tab charts this: bars = queries seen, line = score,
◆ = label flip; dots and table rows open the step detail with factor
breakdowns. The Services tab shows score + vibe per service.

## What the current logs show (2026-09-11 → 2026-10-07, ~2.7k reqs)

- `agentic-knowledge-mapper` → multi-agent debate risk scorer + research synthesizer
- `quai-radar` → blockchain-news KG extractor + daily research-brief writer
- `hive-research-gpu` → paper-surrogate / section-wise summarizer (subagent)
- `kid-learning-lab` → tutor skill coach (embeddings)
- Mesh peers: `axiom-dgx` (11 projects running: Quai-RADAR, Knowledgebase…),
  `harishs-macbook-pro-1` (idle, mlx).

## Caveats

- Prompts are truncated (500–2000 chars), secret-redacted, PII-masked.
- Completions are NOT logged — outputs must be re-derived by re-running.
- Reconstruction recovers templates + pipeline, not exact source.
