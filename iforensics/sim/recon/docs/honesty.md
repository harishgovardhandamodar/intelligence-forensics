# Honesty rules (binding on every report)

1. **Synthetic only.** 900-series SSNs, `4242…` PANs, `example.com`,
   555 phones, `sk-test-` / `ghp_test_` tokens. `TruthRegistry.register`
   and `secrets.check_reserved` refuse anything outside the reserved
   ranges — a generator bug fails loudly, never silently.
2. **Vectors ≠ text.** Embeddings report text accuracy 0, always. Their
   contribution is linkage (near-duplicate families), which only matters
   because it lines up fragments from text-bearing stores.
3. **Amplification is analysis, not a store.** Pooled-vs-single is a
   re-reading of the same residuals, never a new holder of text.
4. **Deterministic or it didn't happen.** Rates, truncations, and flags are
   pure functions of turn index / fixed seed. Same
   `(scenario, seed, n_turns, surface_subset)` → identical report on any
   machine.
5. **Monotone cumulative.** Accuracy over growing surface prefixes never
   steps down, because the text pool only grows. A step down is a bug.
6. **Every claim carries score + coverage + caveats.** Recovered counts,
   per-field accuracy, and the non-claims below travel with every number.
7. **No live-provider measurement.** The framework measures a *model* of a
   provider. Co-served live traffic shows retention only — no accuracy,
   because live traffic has no ground truth.
8. **Server-side scoring.** The CLI prints numbers the server computed; it
   contains no scoring logic.
9. **Ledgered runs.** Parameters + artifact hashes in a hash-chained JSONL;
   `verify` reports the first break.

## Explicit non-claims

- No pure vector-to-text inversion.
- No statement about any real provider's actual retention.
- No real PII, live prompts, cloud model calls, or exfiltration — ever.
