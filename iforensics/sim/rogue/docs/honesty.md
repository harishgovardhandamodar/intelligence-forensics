# Honesty rules — rogue-agent simulation

What this simulation claims, what it explicitly does **not**, and where it is
designed to fail.

Related: [../README.md](../README.md) · [scenarios.md](scenarios.md) ·
[design/10-rogue-agents.md](../../../../design/10-rogue-agents.md)

## The runtime is a model

`openshell.py` models the **shape** of the NVIDIA OpenShell runtime — a
kernel-isolated sandbox per agent, a deny-by-default policy engine over
filesystem / network / process / credential / memory, a supervisor that checks
egress and brokers credentials, a privacy router, and an append-only
hash-chained audit. It is not a binding to, and makes **no measurement of**,
the real product. Rule ids and reasons are illustrative defaults chosen so a
detection can cite something concrete; they are not a security claim about
OpenShell.

## Nothing is executed

`net.egress`, `proc.spawn`, `cred.use`, `fs.read` and `fs.write` are *decided*,
never performed. There is no `subprocess`, no socket, no filesystem side
effect beyond writing the run's own JSON report under `evidence/rogue-reports/`.
Values are synthetic (the AWS-docs example key shape, a synthetic encoded
blob). The simulation cannot exfiltrate anything.

## Detection is deliberately incomplete

Two scenarios exist to show the detector's blind spots, not to hide them:

- `detect_policy_only` runs with only the kernel-deny layer. It catches the
  crasher and **misses** the polluter that stays inside policy. Recall 0.5 —
  by construction.
- `detect_missed_subtle` exfiltrates through an **approved** endpoint at normal
  volume and low entropy. No deny, no behavioural anomaly, no provenance: the
  detector is expected to **miss it entirely** (recall 0.0). This is the honest
  answer to "can you catch a well-behaved traitor?" — not with this layer set.

Every other scenario reports `recall`, `precision`, false positives and false
negatives; the catalogue is scored, not asserted.

## Findings are grounded, or they are not findings

A verdict without an `audit_id` is not emitted. For allowlisted collusion
(no deny to cite) the ground is the audit entry of the shared-channel write
plus the correlation; for pollution it is the writer's audit entry plus the
taint chain. The audit chain is re-hashed and verified on every run
(`audit_verify.ok`), so a grounded verdict is also a tamper-evident one.

## Not a benchmark

Metrics are computed against the scenario's own declared labels — the
simulation grades itself against its own design, not against a real fleet.
It is a model for reasoning about layered governance, not evidence about any
deployed system.
