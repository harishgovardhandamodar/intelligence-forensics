# 06 — Trust boundaries

What crosses each boundary, in which direction, and what is refused. The
design rule is simple: telemetry flows in, nothing that can act flows out.

Related: [privacy.md](privacy.md) · [ethics.md](ethics.md) ·
[01-system-context.md](01-system-context.md) ·
[07-agent-swarm.md](07-agent-swarm.md)

## Boundaries and crossings

```mermaid
flowchart TB
    subgraph Z0["Zone 0 · foreign systems (never touched)"]
        REPO["service repos<br/>no access, no clones"]
        PEERN["peer nodes<br/>no probes, no exec"]
    end
    subgraph Z1["Zone 1 · fox telemetry (read-only)"]
        FDB[("fox_services.db<br/>ro bind /fox-data")]
        FAPI["fox :8210 API<br/>stats · mesh · queue"]
    end
    subgraph Z2["Zone 2 · this container (untrusted output)"]
        APP["dashboard + agents"]
        EV[(evidence/)]
        RC[(reconstructions/)]
    end
    subgraph Z3["Zone 3 · local model"]
        OLL["Ollama :11434<br/>qwen3.8:27b only"]
    end
    subgraph Z5["Zone 5 · swarm workers (one container per role)"]
        WK["profiler/critic/security<br/>1x GPU each<br/>./evidence only"]
        WG["gather<br/>no GPU<br/>./evidence + /fox-data:ro"]
    end
    subgraph Z6["Zone 6 · action ledger (append-only)"]
        LG["evidence/ledger/<br/>hash-chained JSONL<br/>hashes + pointers, no prompts"]
    end
    subgraph Z4["Zone 4 · viewers"]
        BR["browsers<br/>LAN / tailnet, no auth"]
    end
    FDB -->|"SELECT only<br/>snapshot copy"| APP
    FAPI -->|"GET only<br/>best-effort"| APP
    APP -->|"prompts (masked heads)<br/>never secrets"| OLL
    OLL -->|"completions"| APP
    APP -->|"charts · briefs<br/>scaffolds"| BR
    APP -->|"enqueue profile/critic"| WK
    APP -->|"enqueue gather"| WG
    WK -->|"results + artifact sha"| APP
    WK -->|"prompts (masked heads)"| OLL
    OLL -->|"completions"| WK
    WK -->|"task.claimed/completed"| LG
    APP -->|"run.start/complete"| LG
    APP -.->|"REFUSED: writes"| FDB
    APP -.->|"REFUSED: probes/exec"| PEERN
    APP -.->|"REFUSED: cloud models"| OLL
    WK -.->|"REFUSED: fox-data"| FDB
    WK -.->|"REFUSED: worker-to-worker"| WK
    BR -.->|"no auth →"| APP
```

## Boundary rules (enforced, not advised)

| # | Rule | Enforcement |
|---|------|-------------|
| T1 | Fox DB is never written | `:ro` bind mount; SQLite opened read paths only |
| T2 | No peer contact | No peer IPs/URLs in code; mesh data arrives only via fox gossip reads |
| T3 | Inference is local-only | `IF_MODEL` defaults to `qwen3.8:27b`; `OLLAMA_URL` defaults to loopback/host-internal; no API keys exist to leak |
| T4 | No secrets to hold | Container has no tokens, no keys, no Docker socket — theft yields telemetry summaries, not access |
| T5 | Viewer boundary is explicit | No auth is implemented, so exposure is LAN/tailnet only by deployment (bind + firewall), documented in README, never assumed |
| T6 | Reconstructions are labeled | Every scaffold ships `RECONSTRUCTED.json` + caveats; the UI never presents inference as source |
| T7 | Workers are isolated, least mount wins | One container per swarm role with NVIDIA passthrough; workers run as host UID (`user:`); profilers mount `./evidence` only, only gatherers get `/fox-data:ro`; no worker-to-worker traffic |
| T8 | Destruction needs a recorded human | `prune --apply` refuses without `--approve` (logged to the `ops` ledger); worker `prune` tasks re-check `find_approval` at execution time; the ledger itself is append-only and hash-verified |
