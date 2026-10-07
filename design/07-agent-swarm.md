# 07 — Agent swarm

How forensic work is distributed across isolated container workers with
NVIDIA GPU passthrough, coordinated through a file task queue, and recorded
on a tamper-evident action ledger. Start here for P7.

Related: [trust-boundaries.md](trust-boundaries.md) (zones Z5–Z6, rules
T7–T8) · [interaction.md](interaction.md) · [data-model.md](data-model.md) ·
[01-system-context.md](01-system-context.md)

## Swarm topology: who runs where

```mermaid
flowchart TB
    subgraph HOST["Host axiom · 2x RTX 5080"]
        ORCH["orchestrator<br/>cli.py agent-run --swarm<br/>dashboard POST /api/runs"]
        Q[(evidence/swarm/queue/<br/>pending · claimed · done · failed)]
        LG[(evidence/ledger/<br/>hash-chained JSONL)]
        OL["Ollama :11434<br/>qwen3.8:27b"]
    end
    subgraph W1["swarm-worker container<br/>role profiler · 1x GPU"]
        WP["cli.py swarm-worker<br/>claim · execute · complete"]
    end
    subgraph W2["swarm-worker container<br/>role critic · 1x GPU"]
        WC["cli.py swarm-worker<br/>claim · execute · complete"]
    end
    subgraph WG["swarm-gather container<br/>role gather · no GPU"]
        WG2["collect fox API/DB<br/>fox-data:ro only"]
    end
    ORCH -->|"enqueue profile/critic"| Q
    ORCH -->|"enqueue gather"| Q
    WP -->|"atomic rename claim"| Q
    WC -->|"atomic rename claim"| Q
    WG2 -->|"atomic rename claim"| Q
    WP -->|"result + artifact sha"| Q
    ORCH -->|"collect with timeout"| Q
    WP -->|"task.claimed/completed"| LG
    ORCH -->|"run.start/complete"| LG
    WP -->|"prompts (masked heads)"| OL
    OL -->|"completions"| WP
```

Workers never talk to each other. The queue files are the only coordination
primitive (atomic `rename` elects exactly one claim winner); the ledger is
the only shared truth, and it is append-only.

## Task lifecycle: every state is a file move

```mermaid
sequenceDiagram
    participant O as orchestrator
    participant Q as queue files
    participant W as worker container
    participant L as ledger
    O->>Q: enqueue (pending/task.json)
    O->>L: run.start / task.issued
    W->>Q: rename to claimed/ (atomic win)
    W->>L: task.claimed
    W->>W: execute with timeout
    alt success
        W->>Q: move to done/ + result
        W->>L: task.complete + artifact sha
    else failure, attempts left
        W->>Q: move back to pending
        W->>L: task.failed
    else attempts exhausted
        W->>Q: move to failed/
        W->>L: task.failed
    end
    O->>Q: collect results (or timeout)
    Note over W,Q: crashed worker = stale claim<br/>mtime recovery requeues
```

A task whose worker dies mid-claim is not stuck: claims older than the
staleness window are moved back to pending with `attempts` bumped, so the
next live worker picks it up. After `MAX_ATTEMPTS` it parks in `failed/`
for a human.

## Ledger: tamper evidence without a blockchain

```mermaid
flowchart LR
    G["genesis:run_id"] --> E1["seq 1<br/>run.start"]
    E1 --> E2["seq 2<br/>task.claimed"]
    E2 --> E3["seq 3<br/>task.complete<br/>artifact sha"]
    E3 --> VN{"verify:<br/>recompute all hashes?"}
    VN -->|"match"| OK["ok: N checked"]
    VN -->|"mismatch at seq k"| BR["BROKEN:<br/>entry hash or link"]
```

Each entry commits to the previous entry's hash (`prev_hash`) and carries
the SHA-256 of any artifact it produced. Editing, deleting, or reordering
an entry breaks verification at exactly that sequence number
(`cli.py ledger verify --run …`, `GET /api/swarm/verify`). The ledger holds
hashes and pointers only — prompt text stays in the referenced artifacts.

## Isolation: one container per role, least mount wins

| Role | GPU | Mounts | May touch |
|---|---|---|---|
| profiler / critic / security / any | 1 × GPU | `./evidence` only | collected evidence, queue, ledger |
| gather | none | `./evidence` + `/fox-data:ro` | fox telemetry (read-only), queue, ledger |
| orchestrator (host/CLI) | n/a | repo checkout | everything, incl. run manifests |

All worker containers run as the host UID (`user:` directive): root-owned
files on the shared `./evidence` volume once broke host-side ledger appends
(P7.35). Foreign prompt text is processed inside profiler containers and
fenced as untrusted data before reaching any model — see T8 and the D1
fencing in `ollama_client.py`.

## Destructive actions need a human

`prune` (and any future `export`) cannot run on a bare instruction:

```mermaid
flowchart TB
    OP["operator"] -->|"ledger approve --run R --subject S"| L[(ledger)]
    O2["orchestrator / CLI"] -->|"enqueue prune + approval=S"| Q2[(queue)]
    W3["ops worker"] -->|"find_approval(R, S)?"| L
    L -->|"present"| EX["execute + record"]
    L -->|"absent"| RF["refuse: PermissionError"]
```

`cli.py prune --apply` refuses without `--approve '<reason>'` and records
the approval on the `ops` ledger first. The worker re-checks the chain at
execution time, so a forged queue file alone cannot trigger deletion.
