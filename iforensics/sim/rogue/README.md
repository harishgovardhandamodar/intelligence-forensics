# Rogue-agent framework (`iforensics/sim/rogue/`)

Modular, reproducible simulation of a fleet of autonomous agents in which some
turn **rogue**, some **collude** in cells, and some **pollute** shared state —
with layered detection, and every finding **grounded** in a concrete
[NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell) policy decision and
hash-chained audit entry.

**Single source of truth:** the modeled runtime is `openshell.py`; behaviour
scripts are `behaviors.py`; the exhaustive catalogue is `scenarios.py`;
detection is `detect.py`; the engine is `engine.py`. The dashboard is the
server — the framework is adapters, docs, route map and tests, never a second
copy of the engine.

## Reproduce

```bash
# one scenario (no server needed: pure engine, deterministic)
python3 -c "from iforensics.sim import rogue; print(rogue.run_scenario('collude_split_payload')['detection']['metrics'])"

# the whole catalogue's detection coverage
python3 - <<'PY'
from iforensics.sim import rogue
for s in rogue.scenarios():
    r = rogue.run_scenario(s["id"], persist=False)
    m = r["detection"]["metrics"]
    print(f'{s["id"]:30s} recall={m["recall"]} precision={m["precision"]} '
          f'fp={m["false_positive"]} fn={m["false_negative"]}')
PY

# framework test mirror
python3 -m pytest tests/test_rogue.py -q
```

## Layers

- **OpenShell model** — deny-by-default policy over filesystem, network,
  process, credential and memory; supervisor network check; privacy router;
  credential brokering; append-only hash-chained audit.
- **Swarm** — 57 scenarios across single rogues, rogue swarms, colluding
  cells, polluting agents, detection configurations and benign controls.
- **Detection** — policy (denies), behaviour (allowed-but-suspicious), graph
  (collusion cells), provenance (pollution taint). A `mode` select exposes the
  honest coverage gap: `policy_only` misses allowlisted colluders and
  polluters.
- **Grounding** — every verdict carries the `audit_id`, rule id, layer and
  reason of the decision that produced it. A verdict without an audit id is
  not a verdict.

## What this framework does NOT claim

- The OpenShell runtime is a **model**, not the real product; no measurement of
  it is made. Rules are illustrative defaults.
- Nothing is executed: `net.egress`, `proc.spawn` and `cred.use` are *decided*,
  never performed. The swarm is synthetic.
- Detection is not total: `detect_missed_subtle` and `detect_policy_only`
  deliberately show cases the detector is expected to miss (see
  `docs/honesty.md`).

## Layout

`openshell.py` (modeled runtime) · `behaviors.py` (action scripts) ·
`scenarios.py` (57 specs, diagrams) · `detect.py` (4 layers + metrics) ·
`engine.py` (run · persist) · `api/` (route map) · `docs/` · tests live in
`tests/test_rogue.py`.
