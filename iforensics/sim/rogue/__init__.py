"""Rogue-agent swarm simulation — detection grounded in NVIDIA OpenShell.

An autonomous fleet (``iforensics/sim/rogue/``) where some agents turn rogue,
collude in cells, or pollute shared state. Every action is decided by a
deterministic **model** of the NVIDIA OpenShell runtime (sandbox · policy
engine · supervisor · privacy router · hash-chained audit), and every finding
is grounded to the exact rule and audit decision that produced it.

Public surface:

    from iforensics.sim.rogue import run_scenario, scenarios, categories
    run_scenario("collude_split_payload")          # -> full grounded report
    scenarios()                                     # -> exhaustive catalogue

Honesty: the OpenShell runtime here is a model, not the real product; the
swarm is synthetic; nothing is executed (`net.egress`, `proc.spawn`,
`cred.use` are decided, never performed).
"""
from __future__ import annotations

from .engine import list_runs, load_run, reset, run_scenario
from .openshell import APPROVED_ENDPOINTS, PolicyEngine, Rule
from .scenarios import by_category, categories, get, scenarios

__all__ = [
    "run_scenario", "list_runs", "load_run", "reset",
    "scenarios", "categories", "by_category", "get",
    "PolicyEngine", "Rule", "APPROVED_ENDPOINTS",
]
