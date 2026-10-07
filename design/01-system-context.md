# 01 — System context

What is in the box, what is outside it, and what runs where.
`intel-forensics` is one container (port 8211) that watches the fox-services
telemetry stream and reconstructs what the other nodes on the mesh are
building — without ever seeing their repositories.

Related: [02-uml.md](02-uml.md) · [interaction.md](interaction.md) ·
[data-model.md](data-model.md) · [trust-boundaries.md](trust-boundaries.md)

## Context: the box and its neighbours

```mermaid
flowchart TB
    subgraph US["People and callers"]
        B["Browser<br/>the :8211 dashboard<br/>6 tabs incl. Design"]
        OP["Operator CLI<br/>cli.py"]
    end
    subgraph BOX["This app — intel-forensics :8211"]
        DASH["dashboard.py<br/>FastAPI · 6 tabs · SVG charts"]
        INV["Investigator<br/>fingerprint · infer · score"]
        AGT["Agentic runs<br/>scout · profiler · critic · reporter"]
        BLD["Builder<br/>reconstruct · progression"]
        EV[(evidence/<br/>snapshots + runs)]
        RC[(reconstructions/<br/>inferred scaffolds)]
    end
    subgraph OUT["Outside the box"]
        FOX["fox-services :8210<br/>llm_usage telemetry<br/>mesh · docker · stats"]
        FDB[(fox_services.db<br/>mounted read-only<br/>as /fox-data)]
        OL["Ollama :11434<br/>qwen3.8:27b local only"]
        PEER["Mesh peers<br/>observed via fox gossip<br/>never probed directly"]
    end
    B --> DASH
    OP --> INV
    OP --> AGT
    DASH --> EV
    DASH --> RC
    INV --> FOX
    INV --> FDB
    AGT --> OL
    AGT --> EV
    BLD --> RC
    FOX -.->|"gossip (read-only)"| PEER
```

Every arrow is a real integration, and every arrow points *inward*: this app
only ever reads. It never writes to the fox DB, never calls a peer, never
touches a foreign repo. The single outbound inference path (agents → Ollama)
stays on localhost with a local-only model — see [privacy.md](privacy.md).

## Container: one image, four attachments

```mermaid
flowchart LR
    IMG["image<br/>python:3.12-slim<br/>fastapi + uvicorn"]
    IMG --> P["port 8211<br/>0.0.0.0 → LAN + tailnet"]
    IMG --> R1["/fox-data:ro<br/>fox SQLite (never written)"]
    IMG --> R2["./evidence:rw<br/>snapshots · reports · runs"]
    IMG --> R3["./reconstructions:rw<br/>inferred scaffolds"]
    IMG --> H["host.docker.internal<br/>fox :8210 · ollama :11434"]
```

No Docker socket, no Tailscale socket, no secrets: the container cannot act on
the fleet even if compromised — it can only read telemetry and serve charts.
