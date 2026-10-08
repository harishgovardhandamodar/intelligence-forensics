# Insider Recon Instructions — modular `recon` framework build

> **Detailed Plan of Action & Instructions for the Coding Agent**
>
> Build a complete, modular, reproducible simulation framework named
> `recon_framework` (or integrate under `iforensics/sim/recon/` if extending
> the existing codebase). The framework models a malicious insider (or
> compromised internal system) at an LLM provider who can read residual data
> surfaces, even when the product claims "stateless inference." It quantifies
> reconstruction of synthetic sensitive values from each surface alone, from
> cumulative combinations, and via cross-turn amplification.
>
> All work must obey the honesty, ethics, and privacy rules already
> established in the project (`ethics.md`, `privacy.md`,
> `trust-boundaries.md`).

## 0. Repo mapping (read this first — do not rebuild what exists)

This repo already runs the P14 stateless-inference simulation end to end.
The modular package **must reuse it as the single source of truth** rather
than duplicating retention logic, generators, or scoring:

| Plan piece | Already lives at | Reuse as |
|---|---|---|
| 8 residual surfaces (retention policies) | `iforensics/sim/reconstruction.py::_residuals` + `SURFACES`, `STORE_IDS`, `RATE`, `HEAD_CHARS`, `TRACE_CHARS` | engine backing for `core/surfaces/*` (policy metadata + `read()` over `ReconState`) |
| Deterministic sampling | `_frac` / `_pick` / `stable_seed` in `reconstruction.py` | import directly — never re-derive rates |
| Synthetic generators | `iforensics/sim/sensitive.py::generate` + `FIELD_GENERATORS` | backing for `core/secrets.py` |
| Assembly / linkage / amplify / metrics | `structure_attack`, `_linkage`, `per_turn_score`, `score_texts`, `build_report` in `reconstruction.py`; `attacks` + `embeddings` in `iforensics/sim/` | backing for `core/assembly.py`, `linkage.py`, `amplify.py`, `metrics.py` |
| Scenarios | `SCENARIOS`, `build_session`, `run_session` in `reconstruction.py` | backing for `scenarios/*` |
| Vector collection (harvest now / consume later) | `iforensics/sim/harvest.py` (`ResidualCollection`, `STRATEGY`) | backing for collection touchpoints |
| Live co-serving (`u-live-*`) | `coserve_events`, `live_users`, `live_user_for` in `reconstruction.py` | backing for live scenario adapters |
| API routes | `dashboard.py::/api/recon/*` (surfaces, begin, ingest, reconstruct, report, run, residuals, runs, run, reset, collection, consume, harvest-live, coserve, live-users) | backing for `api/routes.py` mapping |
| Stdlib client | `recon_client/` (`api.py`, `app.py`) | reference for `client/run.py` (transport + presentation only) |
| Hash-chained ledger | `iforensics/ledger.py::append` / `verify` | backing for `ledger/chain.py` |
| Design + honesty rules | `design/08-reconstruction-simulation.md`, `design/ethics.md`, `design/privacy.md`, `design/trust-boundaries.md` | normative inputs for `docs/` |
| Existing tests | `tests/test_reconstruction.py`, `tests/test_recon_collections.py` | must keep passing; new `tests/` mirror the plan's files |

New code this plan adds: the `iforensics/sim/recon/` package skeleton,
`SurfacePolicy`/`Residual` abstractions, staged policy modules for surfaces
beyond the original eight, mitigations, framework docs, the framework CLI,
and the framework test-suite mirror. New surfaces stay **policy-complete,
engine-staged** (deterministic `retain()` + tests) until a tracked rollout
wires them into `SURFACES` — never half-wired.

## Non-negotiable constraints (enforce in code and tests)

- Synthetic data only. Use only reserved/test values (900-series SSNs,
  `4242…` PANs, `example.com` emails, 555 phones, `ghp_test_` / `sk-test-`
  tokens, TEST routing numbers, etc.). Ground truth is registered
  server-side; the "insider" view never sees the raw truth.
- Embeddings / vectors report text accuracy = 0. They only contribute
  linkage (near-duplicate families). Never claim pure vector-to-text
  inversion.
- Amplification is an analysis layer, not a store.
- Retention rates, truncation lengths, and full-prompt flags are
  deterministic constants (not random draws). Two machines with the same
  `(scenario, seed, n_turns, surface_subset)` must produce identical reports.
- Every published claim carries score, grade/coverage, and caveats.
- No live prompts, no real PII, no cloud model calls, no network
  exfiltration.
- Cumulative accuracy is monotone non-decreasing by construction.
- All scoring happens server-side. The client is pure transport +
  presentation.
- Reproducible ledger of every run (hash-chained JSONL of parameters +
  artifact hashes).

## Target directory layout

```
iforensics/sim/recon/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── retention.py              # RATE / TRUNC re-export + staged-surface rates
│   ├── secrets.py                # generators + TruthRegistry over sensitive.py
│   ├── surfaces/                 # one module per residual surface
│   │   ├── __init__.py
│   │   ├── base.py               # Turn/Residual dataclasses, SurfacePolicy ABC
│   │   ├── logging.py            # engine-backed (P14 surface)
│   │   ├── billing.py            # engine-backed
│   │   ├── embeddings.py         # engine-backed, text accuracy 0
│   │   ├── cache.py              # engine-backed
│   │   ├── training.py           # engine-backed
│   │   ├── infrastructure.py     # engine-backed
│   │   ├── human_ops.py          # engine-backed
│   │   ├── api_gateway.py        # staged policy module
│   │   ├── rate_limit_quota.py   # staged policy module
│   │   ├── apm_error.py          # staged policy module
│   │   ├── waf_dlp.py            # staged policy module
│   │   ├── product_analytics.py  # staged policy module
│   │   ├── feature_store.py      # staged policy module
│   │   ├── rag_index.py          # staged policy module
│   │   ├── tool_use.py           # staged policy module
│   │   ├── session_correlation.py# staged policy module
│   │   ├── backup_snapshot.py    # staged policy module
│   │   └── gpu_debug.py          # staged policy module (exotic / low-rate)
│   ├── assembly.py               # position-wise merge over structure_attack
│   ├── linkage.py                # families over engine _linkage
│   ├── amplify.py                # pooled vs single-turn over engine
│   └── metrics.py                # solo / cumulative / curves over build_report
├── mitigations.py                # retention caps, never-log-full, DLP sweep
├── scenarios/                    # adapters over SCENARIOS + build_session
│   ├── __init__.py
│   ├── health.py
│   ├── finance.py
│   ├── coding_api_keys.py
│   ├── support_tickets.py
│   ├── hr_onboarding.py
│   ├── devops_deploy.py
│   ├── legal_contracts.py
│   ├── sales_crm.py
│   └── data_engineering.py
├── attacks/
│   ├── __init__.py
│   ├── progressive.py
│   ├── near_dup.py
│   └── membership.py
├── api/
│   ├── __init__.py
│   └── routes.py                 # route catalogue mapping to /api/recon/*
├── client/
│   ├── __init__.py
│   └── run.py                    # stdlib-only CLI (transport + presentation)
├── ledger/
│   ├── __init__.py
│   └── chain.py                  # append/verify over iforensics/ledger.py
├── tests/
│   ├── test_reproducibility.py
│   ├── test_monotone.py
│   ├── test_embeddings_zero_text.py
│   ├── test_assembly.py
│   └── test_surfaces.py
├── docs/
│   ├── surfaces.md               # catalogue of every surface + rates
│   ├── honesty.md
│   └── ethics_gates.md
└── README.md
```

## Phase 0 — Bootstrap & foundations (Day 1)

1. Create the package skeleton (`iforensics/sim/recon/`; stdlib + numpy
   only — FastAPI lives in the existing dashboard, not here).
2. Implement `core/secrets.py`:
   - Generators for every synthetic shape, backed by `sensitive.generate`.
   - Reserved-range validators (reject anything outside the test ranges).
   - A `TruthRegistry` that holds ground-truth values for a run (never
     exposed to residual stores).
3. Implement `core/retention.py`:
   - Re-export `RATE`, `HEAD_CHARS`, `TRACE_CHARS`, `STORE_IDS`,
     `SURFACES` from the engine (single source of truth — no copies).
   - `STAGED_RATES` for the staged surfaces: deterministic fractions with
     retention-window comments.
4. Implement `core/surfaces/base.py`:
   - `Turn` + `Residual` dataclasses (surface name, turn_id, text_fragment
     or None, vector or None, metadata dict, linkage_key).
   - Abstract `SurfacePolicy` with `retain(turn) -> list[Residual]`,
     `read()`, `clear()`.
5. First unit tests: secret generators produce only reserved values;
   retention constants are deterministic and identical to the engine's.

**Acceptance:** new framework tests pass; secrets never contain
real-looking PII outside the reserved ranges.

## Phase 1 — Core residual surfaces (Days 2–3)

Engine-backed modules for the original eight surfaces exactly as specified
in `08-reconstruction-simulation.md`: each module carries the policy card
(rate, truncation, full-prompt flag) and reads live engine records — the
retention logic itself stays in `reconstruction._residuals`.

Then the staged policy modules (`api_gateway`, `tool_use`,
`session_correlation`, `backup_snapshot`, `rate_limit_quota`, `apm_error`,
`waf_dlp`, `product_analytics`, `feature_store`, `rag_index`, `gpu_debug`):
full `SurfacePolicy` implementations with deterministic `retain()` (seeded
fractions of turn index — no RNG state), each with an in-memory store behind
`read()`/`clear()`.

`embeddings.py` must: expose the 384-d deterministic vector path, report
text accuracy 0 always, and support near-duplicate family detection via
`linkage.py`.

**Acceptance:** each surface exercisable in isolation; `embeddings` alone
always yields text accuracy 0; identical seeds produce identical residual
sets; staged modules are deterministic across processes.

## Phase 2 — Assembly, linkage & metrics (Days 3–4)

1. `core/assembly.py` — extract secret-shaped spans, group by shape,
   position-wise merge (known characters win); return recovered value +
   coverage + confidence. Backed by the engine's structure attack.
2. `core/linkage.py` — cluster vectors / session IDs into families; report
   purity, coverage, family count. Backed by engine `_linkage`.
3. `core/amplify.py` — pool residuals across turns; single-turn mean vs
   pooled accuracy → amplification delta. Analysis layer only, never a
   store.
4. `core/metrics.py` — `solo()`, `cumulative()` (monotone by
   construction), `curves()` over `build_report`.

**Acceptance tests (mandatory):** cumulative strictly monotone
non-decreasing; embeddings alone → text accuracy 0; amplification delta
positive under partial disclosure; assembly recovers full values from
complementary fragments.

## Phase 3 — Scenarios & attack strategies (Day 5)

Scenario adapters over `SCENARIOS` + `build_session` for every workload
(health, finance, coding_api_keys, support_tickets, hr_onboarding,
devops_deploy, legal_contracts, sales_crm, data_engineering), each exposing
`truth()`, `turns(n, seed)`, and `run(n, seed)` against the engine.

Attack modules over the engine: progressive (growing turn sets),
near-dup (linkage + assembly), membership (candidate presence in the pool).

**Acceptance:** identical `(scenario, seed, n)` → identical numbers on two
machines; complete disclosure reaches 1.0; partial regimes plateau below
1.0 by design.

## Phase 4 — API, client, ledger & dashboard integration (Days 6–7)

1. `api/routes.py` — catalogue mapping every framework operation to its
   live `/api/recon/*` route (surfaces, begin, ingest, reconstruct,
   report, run, residuals, runs, run, reset, collection, consume,
   harvest-live, coserve, live-users), plus the co-serve/live-users additions.
2. Stdlib-only CLI (`client/run.py`): run/report/inspect/reset/ledger-verify
   against the dashboard. No scoring logic in the client — transport +
   presentation only.
3. `ledger/chain.py`: append/verify over `iforensics/ledger.py`.
4. Dashboard already carries the Recon tab, Stateless recon tab, and Live →
   Stateless recon subtab with ledger verification status — document the
   mapping, do not duplicate UI.

**Acceptance:** framework CLI drives a scenario end to end with a verifiable
ledger entry; reset clears all state.

## Phase 5 — Mitigations, documentation & final hardening (Day 8)

1. `mitigations.py` sweep: per-user retention cap, never-log-full-value,
   DLP modes (off/audit/redact/block), cache TTL + embedding-encryption
   flags — each a pure record transform + a curve-flattening measurement.
2. The three docs: `docs/surfaces.md`, `docs/honesty.md`,
   `docs/ethics_gates.md` (flowchart from `design/ethics.md` applied here).
3. Full framework test suite: every surface, every scenario,
   reproducibility, mitigation sweeps.
4. README: reproduction commands, interpretation guide (solo / cumulative /
   amplification), explicit non-claims (no live provider measurement, no
   pure vector inversion, synthetic only).

## Implementation order the agent must follow

1. Skeleton + secrets + retention constants + base surface class + first tests.
2. Original eight surfaces (engine-backed).
3. Assembly + linkage + metrics + monotone/zero-text tests.
4. Staged surfaces (policy-complete, engine rollout tracked, never half-wired).
5. All scenarios + attack strategies.
6. API mapping + CLI + ledger.
7. Mitigations + docs + full test suite.
8. Dashboard integration = documentation of the existing mapping.

## Definition of done

- All listed surfaces implemented (eight engine-backed; rest policy-complete
  with deterministic `retain()` + tests).
- All scenarios runnable and reproducible.
- Solo / cumulative / amplification metrics correct and tested.
- Embeddings alone always report text accuracy 0.
- Cumulative is monotone.
- Ledger verifies cleanly.
- Client never contains scoring code.
- Every report carries scores, coverage, and the honesty caveats.
- `pytest` passes fully (existing + framework suites).
- A single command runs any scenario and produces a comparable,
  hash-chained report.

Start with Phase 0. After each phase, run the acceptance tests for that
phase before proceeding. Prefer pure functions and immutable data where
possible so the simulation stays easy to reason about and bit-reproducible.
