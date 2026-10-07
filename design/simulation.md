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

## Disclosure mechanics: two complementary paths

Carrier clustering (cosine over full texts) groups near-identical
repetitions; it fragments as soon as carriers are paraphrased (measured
0.08–0.16 across rewordings — near-unrelated). The robust path is
structural:

```mermaid
flowchart LR
    Q1["different carriers<br/>same masked secret"] --> X["extract secret-shaped spans"]
    X --> G["merge by shape +<br/>known-char agreement"]
    G --> A["position-wise assembly<br/>every known char wins"]
    A --> S["full value + coverage"]
```

Masks of one value share a shape (`###-##-####` covers `***-**-6789`,
`123-**-****` and the bare secret); conflicting values split into separate
groups even at identical shape. Membership probes compare the candidate
against extracted spans, not whole sentences, so carrier wording drops out
(logged secrets ~0.56–0.75, unseen ~0.0).

Each query alone reveals little; together they reveal everything. The
progression curve (accuracy vs number of queries) is the chart that matters:
it is monotone non-decreasing by construction, and its slope measures how
fast repetition burns a secret.

## What the results mean

- **Complete-disclosure regimes recover at 1.0 through paraphrase and
  distractor noise** (health, finance, api-keys): the structural path is
  unaffected by carrier rewording that defeats pure cosine clustering.
- **Partial regimes plateau below 1.0** (`coding_secrets`, final slot never
  disclosed: 0.93/0.97) — the curve levels off instead of completing, which
  is the measurable payoff of never logging the full value.
- **Membership inference** separates logged secrets (~0.56–0.75, higher when
  stored verbatim) from unseen values (~0.0) with wide margin.
- The finding is the *curve slope*, not the endpoint: accuracy climbs
  steeply within 2–3 repetitions in every regime.
- **Mitigations this setup can test**: per-user retention limits (fewer stored
  pairs = flatter curve), never logging the full value (partial regime —
  measured plateau), mask normalization before embedding (destroys the
  positional signal), and embedding encryption at rest.

## Honest limits

- The mock gateway *echoes* the masked secret; a real LLM paraphrases, which
  spreads the signal across more varied surface text (harder assembly, same
  clustering principle).
- Hash embeddings are order-insensitive bags; transformer embeddings separate
  paraphrases better and exact strings worse. Both backends are supported;
  conclusions should be re-checked per backend.
- Milvus is optional infrastructure here, not load-bearing: the numpy store
  implements the same API, and `connect()` degrades with a note.
