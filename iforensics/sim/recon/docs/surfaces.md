# Surface catalogue

Eight engine surfaces (exact P14 behavior) plus eleven staged policy
modules. Rates are deterministic fractions of the turn index — identical on
any two machines for the same `(scenario, seed, n_turns)`.

## Engine surfaces (`core/surfaces/*.py`, retention in `reconstruction.py`)

| surface | keeps whole prompt when | always keeps | window / note |
|---|---|---|---|
| `logging` | 15% safety-sampled turns | 180-char head + completion | observability |
| `billing` | 9% dispute-sampled turns | token/byte meters + prompt SHA-256 | meters join on hash |
| `embeddings` | **never (text accuracy 0)** | 384-d hash vector | linkage only |
| `cache` | exact re-send (full) / ≥24-char shared prefix | newest KV snapshot (newest turn only) | TTL eviction honest |
| `training` | 14% eval + 8% staging turns | — | 30d eval / pre-deletion staging |
| `infrastructure` | 16% over-TTL queue + 7% snapshot turns | 120-char trace | object-store versions |
| `human_ops` | 12% support-view (90-char window) + 5% raw paste, only when a masked secret is present | — | strongest; easiest to switch off |

`amplification` is an analysis view over the above, not a store — it must
never appear in a store list or a harvest filter twice.

## Staged surfaces (`staged=True`, policy-complete, engine rollout tracked)

| surface | whole fraction | head | window |
|---|---|---|---|
| `api_gateway` | 1/20 | 200 | access logs, 7d |
| `tool_use` | 1/12 | 160 | tool-call audit, 30d |
| `session_correlation` | 1/25 | 64 | join keys, 90d |
| `backup_snapshot` | 1/50 | 0 | nightly snapshots, 35d |
| `rate_limit_quota` | never | 48 | counter keys, 24h |
| `apm_error` | 1/15 | 220 | error traces, 14d |
| `waf_dlp` | 1/30 | 120 | rule excerpts, 90d |
| `product_analytics` | never | 80 | event properties, 13mo |
| `feature_store` | 1/40 | 0 | raw-text features, 400d |
| `rag_index` | 1/8 | 512 | indexed chunks, 400d |
| `gpu_debug` | 1/100 | 96 | crash dumps, 3d (exotic) |

Staged modules implement `SurfacePolicy.retain()` deterministically with an
in-memory store behind `read()`/`clear()`. Wiring one into `SURFACES` is a
tracked rollout — never half-wired.

## Honesty notes (binding)

- Vectors report text accuracy **0**, always; they contribute linkage only.
- A store that kept every prompt would flatten the per-surface gradient —
  rates are deliberately modest so the measurement means something.
- KV snapshots linger: only the newest turn keeps one.
- Live co-served traffic (`u-live-*`) carries no ground truth: retention
  counts only, never accuracy.
