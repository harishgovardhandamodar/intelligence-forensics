# stateless-inference — reconstructed

Inferred build: **stateless-inference residual surfaces (P14 model)**

prompts -> 8 residual surfaces -> vector collection -> reconstruction (harvest now, consume/attack later)

- Requests observed: 330, tokens: 0
- Models: none — no LLM is involved in the residual path
- Query types: {'residual_ingest': 330}
- Pipeline: capture_prompt -> residual_retention -> vector_collection.harvest -> reconstruction.consume

> This entry is a **model**, not telemetry: no service in the mesh streams
> these prompts. It documents what a provider that advertises *stateless
> inference* retains anyway — observability logs, token meters, embedding
> vectors, caches, training staging, infrastructure leftovers, human support
> tooling — and how those residues are turned into a reconstruction.

## The strategy

| phase | when | what happens |
| --- | --- | --- |
| **harvest now** | on every ingest | each text-bearing residual is embedded and appended to the `recon_residuals` vector collection, carrying provenance (`user_id`, `run_id`, `surface`, `kind`, `field`, `turn`) but **no ground truth** |
| **consume / attack later** | whenever the analyst gets to it | the collection is read back and scored against whatever truth has been registered by then — repeatable, without re-collecting anything |

## Files
- `inferred_pipeline.py` — runnable scaffold (replays every stage against `/api/recon/*`)
- `prompts/template_1.txt` — recovered prompt template
- `RECONSTRUCTED.json` — machine-readable reconstruction
