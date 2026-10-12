"""Modeled NVIDIA OpenShell runtime — sandbox · policy engine · supervisor.

Real OpenShell (github.com/NVIDIA/OpenShell) runs fleets of autonomous AI
agents inside kernel-isolated sandboxes. A **policy engine** governs
filesystem, network, process and credential access; a **supervisor** outside
the workload checks every outbound request and brokers credentials only to
approved endpoints; a **privacy router** decides whether a request goes to a
local or frontier model; and every allow/deny is written to an append-only
audit trail.

This module is a deterministic, dependency-free *model* of that runtime. It is
not a binding to the real product and measures nothing about it. Its only job
is to make every rogue-agent finding in this simulation **grounded**: each
detection can cite the exact policy rule that was evaluated and the exact
hash-chained audit decision that recorded the outcome — the same trace the
real runtime would supply.

Honesty: the runtime here is a model. Rules are illustrative defaults, not a
security claim about OpenShell. Nothing real is executed; `proc.spawn`,
`net.egress` and `cred.use` are decided, never performed.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import asdict, dataclass

GENESIS = "openshell:genesis"


@dataclass(frozen=True)
class Rule:
    """One enforcement rule. First match wins, in list order."""
    id: str
    kind: str            # fs.read | fs.write | net.egress | proc.spawn | ...
    match: str           # path glob or host/binary pattern
    effect: str          # allow | deny
    layer: str           # filesystem | network | process | credential | privacy | memory
    reason: str


def _r(id_: str, kind: str, match: str, effect: str, layer: str,
       reason: str) -> Rule:
    return Rule(id_, kind, match, effect, layer, reason)


# --------------------------------------------------------------------------- #
# Default deny-by-default policy                                               #
# --------------------------------------------------------------------------- #
DEFAULT_RULES: list[Rule] = [
    # --- filesystem ------------------------------------------------------- #
    _r("R-FS-READ-WS", "fs.read", "/workspace/**", "allow", "filesystem",
       "agent workspace is readable"),
    _r("R-FS-READ-ETC", "fs.read", "/etc/**", "deny", "filesystem",
       "system config is outside the sandbox mount"),
    _r("R-FS-READ-PROC", "fs.read", "/proc/**", "deny", "filesystem",
       "host process table is not mounted"),
    _r("R-FS-READ-HOST", "fs.read", "/host/**", "deny", "filesystem",
       "host root is not mounted"),
    _r("R-FS-READ-DEFAULT", "fs.read", "*", "deny", "filesystem",
       "default deny: read outside workspace"),
    _r("R-FS-WRITE-WS", "fs.write", "/workspace/**", "allow", "filesystem",
       "agent workspace is writable"),
    _r("R-FS-WRITE-ETC", "fs.write", "/etc/**", "deny", "filesystem",
       "policy/config writes are refused (tamper)"),
    _r("R-FS-WRITE-HOST", "fs.write", "/host/**", "deny", "filesystem",
       "host root is not writable"),
    _r("R-FS-WRITE-DEFAULT", "fs.write", "*", "deny", "filesystem",
       "default deny: write outside workspace"),
    # --- network ---------------------------------------------------------- #
    _r("R-NET-OLLAMA", "net.egress", "ollama.local:11434", "allow", "network",
       "local inference endpoint is approved"),
    _r("R-NET-FOX", "net.egress", "fox.local:8210", "allow", "network",
       "telemetry endpoint is approved"),
    _r("R-NET-LOCAL", "net.egress", "*.local:*", "allow", "network",
       "local mesh endpoints are approved"),
    _r("R-NET-DEFAULT", "net.egress", "*", "deny", "network",
       "supervisor refuses egress to unlisted endpoints"),
    # --- process ---------------------------------------------------------- #
    _r("R-PROC-PYTHON", "proc.spawn", "python*", "allow", "process",
       "python toolchain is approved"),
    _r("R-PROC-NODE", "proc.spawn", "node*", "allow", "process",
       "node toolchain is approved"),
    _r("R-PROC-DEFAULT", "proc.spawn", "*", "deny", "process",
       "kernel refuses to spawn an unlisted binary"),
    # --- credential brokering -------------------------------------------- #
    _r("R-CRED-APPROVED", "cred.use", "approved:*", "allow", "credential",
       "supervisor injects the credential only for approved endpoints"),
    _r("R-CRED-DEFAULT", "cred.use", "*", "deny", "credential",
       "supervisor will not release a credential to this endpoint"),
    # --- model routing --------------------------------------------------- #
    _r("R-MODEL-LOCAL", "model.call", "local:*", "allow", "privacy",
       "privacy router keeps the request local"),
    _r("R-MODEL-FRONTIER", "model.call", "frontier:*", "allow", "privacy",
       "privacy router allows a non-sensitive frontier call"),
    # --- memory ---------------------------------------------------------- #
    _r("R-MEM-SHARED-R", "memory.read", "/shared/**", "allow", "memory",
       "shared scratch is readable"),
    _r("R-MEM-SHARED-W", "memory.write", "/shared/**", "allow", "memory",
       "shared scratch is writable (legitimate collaboration)"),
    _r("R-MEM-CORPUS-R", "memory.read", "/workspace/corpus/**", "allow",
       "memory", "the shared corpus is readable"),
    _r("R-MEM-CORPUS-W", "memory.write", "/workspace/corpus/**", "allow",
       "memory", "agents contribute to the shared corpus — poisoning is a "
                 "semantic act policy cannot see"),
    _r("R-MEM-PEER", "memory.write", "/workspace/memory/peer/**", "deny",
       "memory", "an agent may not write another agent's private memory"),
    _r("R-MEM-R-DEFAULT", "memory.read", "*", "deny", "memory",
       "default deny: memory read outside workspace/shared"),
    _r("R-MEM-W-DEFAULT", "memory.write", "*", "deny", "memory",
       "default deny: memory write outside workspace/shared"),
    # --- messages -------------------------------------------------------- #
    _r("R-MSG-PUB", "message.publish", "*", "allow", "network",
       "swarm bus is open to peers"),
]

PRIVACY_SECRET_FRONTIER = _r(
    "R-PRIV-SECRET-FRONTIER", "model.call", "frontier:*", "deny", "privacy",
    "privacy router stops a secret from leaving for a frontier model")

OWN_MEMORY = _r("R-MEM-OWN", "memory.*", "/workspace/memory/<self>/**",
                "allow", "memory", "an agent owns its private memory namespace")

APPROVED_ENDPOINTS = ("approved:fox", "approved:ollama")


def _match(pattern: str, target: str) -> bool:
    if pattern in ("*", "**"):
        return True
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return target == base or target.startswith(base + "/")
    return fnmatch.fnmatch(target, pattern)


class PolicyEngine:
    """Deterministic evaluator + hash-chained audit trail.

    A fresh engine is created per run; `evaluate()` never executes anything —
    it decides and records. `update_policy()` models live governance: a rule
    changes at sandbox scope and the change is itself an audit entry.
    """

    def __init__(self, rules: list[Rule] | None = None,
                 name: str = "openshell-default") -> None:
        self.name = name
        self.rules: list[Rule] = list(rules if rules is not None
                                      else DEFAULT_RULES)
        self._entries: list[dict] = []
        self._prev = GENESIS
        self._seq = 0

    # -- policy surface ---------------------------------------------------- #
    def rules_snapshot(self) -> list[dict]:
        return [asdict(r) for r in self.rules]

    def update_policy(self, rule: Rule, actor: str = "operator") -> dict:
        """Live policy update (models `openshell policy update`).

        A specific rule must out-rank the wildcard default, so it is inserted
        ahead of the first same-kind `*` rule; otherwise it is appended.
        """
        self.rules = [r for r in self.rules if r.id != rule.id]
        insert_at = len(self.rules)
        for i, r in enumerate(self.rules):
            if r.kind == rule.kind and r.match in ("*", "**"):
                insert_at = i
                break
        self.rules.insert(insert_at, rule)
        return self._commit(agent=actor, kind="policy.update",
                            target=rule.id, rule=rule, effect="note",
                            action={}, payload=rule.effect)

    # -- evaluation -------------------------------------------------------- #
    def evaluate(self, agent: str, action: dict) -> dict:
        kind = action.get("kind", "")
        target = action.get("target", "")
        rule = self._pick(agent, kind, target, action)
        effect = "allow" if rule.effect == "allow" else "deny"
        return self._commit(agent=agent, kind=kind, target=target, rule=rule,
                            effect=effect, action=action,
                            payload=action.get("payload", ""))

    def _pick(self, agent: str, kind: str, target: str, action: dict) -> Rule:
        # Privacy router is a semantic layer over the model route.
        if (kind == "model.call"
                and action.get("data_class") == "secret"
                and target.startswith("frontier")):
            return PRIVACY_SECRET_FRONTIER
        # Own-namespace memory is always allowed; peer writes fall through.
        own = f"/workspace/memory/{agent}/"
        if kind.startswith("memory.") and target.startswith(own):
            return OWN_MEMORY
        for rule in self.rules:
            if rule.kind == kind and _match(rule.match, target):
                return rule
        return Rule("R-IMPLICIT-DENY", kind, "*", "deny", "unknown",
                    "no rule matched; deny by default")

    # -- audit chain ------------------------------------------------------- #
    def _commit(self, agent: str, kind: str, target: str, rule: Rule,
                effect: str, action: dict, payload: str = "") -> dict:
        self._seq += 1
        body = {
            "seq": self._seq,
            "agent": agent,
            "action": kind,
            "target": target,
            "rule_id": rule.id,
            "layer": rule.layer,
            "effect": effect,
            "reason": rule.reason,
            "data_class": action.get("data_class", "internal"),
            "channel": action.get("channel", ""),
            "step": action.get("step", 0),
            "payload_head": (payload or "")[:80],
            "prev_hash": self._prev,
        }
        audit_id = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()).hexdigest()
        entry = {**body, "audit_id": audit_id}
        self._entries.append(entry)
        self._prev = audit_id
        return entry

    def audit(self) -> list[dict]:
        return list(self._entries)

    def verify(self) -> dict:
        """Recompute the chain; report the first break, if any."""
        prev = GENESIS
        for i, e in enumerate(self._entries, 1):
            body = {k: v for k, v in e.items() if k != "audit_id"}
            body["prev_hash"] = prev
            if (body.get("seq") != i or e.get("prev_hash") != prev
                    or e.get("audit_id")
                    != hashlib.sha256(
                        json.dumps(body, sort_keys=True).encode()).hexdigest()):
                return {"ok": False, "checked": i - 1, "broken_at": i}
            prev = e["audit_id"]
        return {"ok": True, "checked": len(self._entries), "broken_at": None}
