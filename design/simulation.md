# Simulation — embedding reconstruction attacks

What this experiment shows, how it is built, and what to conclude. The
simulation demonstrates that **repeated similar queries leak sensitive
values when a gateway logs query/response embeddings**: masked variants
cluster by cosine similarity, and position-wise assembly of the unmasked
characters recovers the full secret.

Related: [privacy.md](privacy.md) · [trust-boundaries.md](trust-boundaries.md) ·
[01-system-context.md](01-system-context.md)

## Experiment loop

```mermaid
flowchart TB
    subgraph CLIENT["sim/ client (stdlib only)"]
        SC["scenarios/<br/>health · finance · api-keys · secrets"]
        RN["run.py<br/>begin → ingest → attack → report"]
    end
    subgraph SERVER["this app · /api/sim/*"]
        GW["MockGateway<br/>masked response + embed both"]
        ST[(vector store<br/>numpy default · Milvus optional)]
        AT["attacks<br/>progressive · near-dup · membership"]
        AN["analysis<br/>accuracy · curves · report"]
    end
    SC -->|"begin(truth)"| AN
    RN -->|"ingest(prompt, mask)"| GW
    GW -->|"query + response vectors"| ST
    RN -->|"attack(user)"| AT
    AT -->|"clusters · assemblies"| AN
    AN -->|"accuracy vs truth"| RN
```

The client knows the secrets; the server only ever sees masked texts and
embeddings. The attack runs server-side on vectors + texts alone — the same
information a real log holder has.

## Disclosure mechanics

```mermaid
flowchart LR
    Q1["query 1<br/>***-**-6789"] --> C["cosine cluster<br/>same user, sim ≥ 0.6"]
    Q2["query 2<br/>123-**-****"] --> C
    Q3["query 3<br/>123-45-6789"] --> C
    C --> A["position-wise merge<br/>every known char wins"]
    A --> S["123-45-6789<br/>coverage 1.0"]
```

Each query alone reveals little; together they reveal everything. The
progression curve (accuracy vs number of queries) is the chart that matters:
it is monotone non-decreasing by construction, and its slope measures how
fast repetition burns a secret.

## What the results mean

- **8/8 fields recovered at 1.0** across all four scenarios is expected, not
  surprising: the final step of every schedule discloses the full value.
  The finding is the *curve*, not the endpoint — accuracy climbs steeply
  within 2–3 repetitions.
- **Membership inference** separates logged secrets (~0.56–0.74) from unseen
  values (~0.0–0.05) with wide margin on the hash backend.
- **Mitigations this setup can test**: per-user retention limits (fewer stored
  pairs = flatter curve), mask normalization before embedding (destroys the
  positional signal), query dedup (collapses the cluster), and embedding
  encryption at rest (raises the bar from read to break).

## Honest limits

- The mock gateway *echoes* the masked secret; a real LLM paraphrases, which
  spreads the signal across more varied surface text (harder assembly, same
  clustering principle).
- Hash embeddings are order-insensitive bags; transformer embeddings separate
  paraphrases better and exact strings worse. Both backends are supported;
  conclusions should be re-checked per backend.
- Milvus is optional infrastructure here, not load-bearing: the numpy store
  implements the same API, and `connect()` degrades with a note.
