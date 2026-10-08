# Insider-recon framework (`iforensics/sim/recon/`)

Modular, reproducible simulation of a malicious insider at an LLM provider
that keeps residual data despite advertising "stateless inference."
Quantifies reconstruction of **synthetic** sensitive values per surface,
cumulatively, and via cross-turn amplification.

**Single source of truth:** retention logic, generators, and scoring live
in `iforensics/sim/{reconstruction,sensitive,harvest}.py`. This package is
adapters, policy cards, staged modules, mitigations, docs, CLI, and tests —
never a second copy. Full build instructions:
`to-do-insider-recon-instructions.md` (repo root).

## Reproduce

```bash
# one scenario, comparable hash-chained report (server must be up)
/home/fox/codebase/.venv/bin/python -m iforensics.sim.recon.client.run \
  --server http://localhost:8211 run --scenario stateless_coding --n 48 --seed 42

# framework test mirror
/home/fox/codebase/.venv/bin/python -m pytest iforensics/sim/recon/tests/ -q
```

## The three numbers

- **solo** — each surface alone (embeddings 0.0: vectors carry no text,
  only linkage; billing middling; human_ops near 1.0).
- **cumulative** — growing surface prefixes; monotone by construction
  (the text pool only grows).
- **amplification** — one request judged alone vs all requests pooled
  (Δ ≈ +0.75 in the P14 calibration); analysis layer, not a store.

## What this framework does NOT claim

- No measurement of any real provider. It measures a *model* of one.
- No pure vector-to-text inversion (text accuracy of vectors is 0).
- Synthetic values only (see `docs/honesty.md`).
- Live co-served traffic shows retention counts only — never accuracy.

## Layout

`core/` (secrets, retention, surfaces, assembly, linkage, amplify,
metrics) · `scenarios/` (9 workloads) · `attacks/` (progressive,
near-dup, membership) · `mitigations.py` (retention caps, never-log-full,
DLP sweep) · `api/` (route catalogue) · `client/` (stdlib CLI) ·
`ledger/` (hash-chained runs) · `docs/` · `tests/`.
