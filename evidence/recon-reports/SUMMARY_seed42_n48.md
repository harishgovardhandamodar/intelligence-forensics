# Stateless-recon comparative report — seed 42, n=48, 10 scenarios

| scenario | turns | records | fields | pooled | recovered | amp Δ |
|---|---|---|---|---|---|---|
| stateless_aux_history | 48 | 311 | 1 | 1.000 | 1/1 | 0.430 |
| stateless_aux_settlement | 48 | 296 | 2 | 1.000 | 2/2 | 0.736 |
| stateless_chat | 48 | 309 | 2 | 1.000 | 2/2 | 0.788 |
| stateless_coding | 48 | 330 | 2 | 1.000 | 2/2 | 0.749 |
| stateless_devops | 48 | 311 | 3 | 0.667 | 1/3 | 0.587 |
| stateless_exploit_cache | 48 | 320 | 2 | 0.531 | 1/2 | 0.305 |
| stateless_finance | 48 | 302 | 2 | 1.000 | 2/2 | 0.792 |
| stateless_hr | 48 | 321 | 3 | 0.313 | 0/3 | 0.274 |
| stateless_legal | 48 | 316 | 3 | 0.508 | 0/3 | 0.454 |
| stateless_support | 48 | 320 | 2 | 1.000 | 2/2 | 0.790 |

## Solo accuracy per surface

| surface | aux_history | aux_settlement | chat | coding | devops | exploit_cache | finance | hr | legal | support |
|---|---|---|---|---|---|---|---|---|---|---|
| billing | 1.00 | 0.85 | 0.33 | 0.68 | 0.13 | 0.53 | 0.54 | 0.13 | 0.36 | 0.60 |
| cache | 1.00 | 0.92 | 0.89 | 0.83 | 0.61 | 0.53 | 0.88 | 0.29 | 0.41 | 0.95 |
| embeddings | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| human_ops | 1.00 | 1.00 | 1.00 | 1.00 | 0.46 | 0.53 | 1.00 | 0.17 | 0.15 | 0.70 |
| infrastructure | 1.00 | 0.92 | 1.00 | 0.83 | 0.65 | 0.53 | 0.59 | 0.31 | 0.46 | 0.50 |
| logging | 1.00 | 0.92 | 0.61 | 0.83 | 0.39 | 0.53 | 0.85 | 0.31 | 0.24 | 0.70 |
| training | 1.00 | 0.79 | 0.79 | 0.77 | 0.41 | 0.45 | 1.00 | 0.14 | 0.51 | 1.00 |

## Reading
- aux_settlement saturates (1.0): settlement lines add join material without hiding the secret.
- aux_history saturates everything at 1.0 within the archive turns — the upper bound of aux advantage.
- exploit_cache halves distinct disclosures (every prompt doubled): pooled 0.53 vs 1.0 baseline — concentration without breadth.
- embeddings 0.0 everywhere (linkage only). All values synthetic; no vector inversion claimed.
