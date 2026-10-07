"""The design set, served as selectable documents to the Design tab.

Mirrors the fox-services pattern: a FIXED INDEX (not a directory listing),
so traversal attempts 404 like unknown ids; a missing design dir is a state
(available:false), not a crash.
"""
from __future__ import annotations

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN_DIR = os.environ.get("IF_DESIGN_DIR") or os.path.join(BASE_DIR, "design")

MAX_BYTES = 1_000_000

_DOCS: list[dict[str, str]] = [
    {"id": "system-context", "file": "01-system-context.md", "title": "System context",
     "group": "Structure", "kind": "context · container · deployment",
     "answers": "What is in the box, what is outside it, and what runs where"},
    {"id": "uml", "file": "02-uml.md", "title": "UML structure",
     "group": "Structure", "kind": "component · class · package",
     "answers": "Which module owns which responsibility, and how they depend"},
    {"id": "interaction", "file": "interaction.md", "title": "Interaction",
     "group": "Behaviour", "kind": "sequence",
     "answers": "What calls what, in what order, on every major flow"},
    {"id": "activity", "file": "activity.md", "title": "Activity",
     "group": "Behaviour", "kind": "decisions",
     "answers": "What decisions the pipeline makes, and how the UI degrades"},
    {"id": "data-model", "file": "data-model.md", "title": "Data model",
     "group": "Data & assurance", "kind": "ER · lifecycle",
     "answers": "What is stored, how it relates, and how records move through states"},
    {"id": "trust-boundaries", "file": "trust-boundaries.md", "title": "Trust boundaries",
     "group": "Data & assurance", "kind": "zones · crossings · rules",
     "answers": "What crosses each boundary, and what is refused"},
    {"id": "privacy", "file": "privacy.md", "title": "Privacy",
     "group": "Data & assurance", "kind": "gates · measures · residual risks",
     "answers": "What data exists, where it can go, and what provably cannot leave"},
    {"id": "ethics", "file": "ethics.md", "title": "Ethics",
     "group": "Data & assurance", "kind": "constraints · decision check",
     "answers": "The constraints that keep reconstruction honest"},
    {"id": "agent-swarm", "file": "07-agent-swarm.md", "title": "Agent swarm",
     "group": "Structure", "kind": "workers · queue · ledger · GPUs",
     "answers": "How forensic work is distributed, isolated, and recorded"},
    {"id": "simulation", "file": "simulation.md", "title": "Simulation",
     "group": "Data & assurance", "kind": "experiment · attacks · mitigations",
     "answers": "What the reconstruction experiment shows and its limits"},
]

_FENCE_RE = re.compile(r"^\s*```(\w*)\s*$")


class UnknownDoc(KeyError):
    pass


def _entry(doc_id: str) -> dict[str, str] | None:
    for d in _DOCS:
        if d["id"] == doc_id:
            return d
    return None


def _resolve(entry: dict) -> str | None:
    root = os.path.realpath(DESIGN_DIR)
    target = os.path.realpath(os.path.join(root, entry["file"]))
    if not target.startswith(root + os.sep) and target != root:
        return None
    return target if os.path.isfile(target) else None


def _diagram_count(text: str) -> int:
    """Count ```mermaid opening fences."""
    n = 0
    for line in text.split("\n"):
        m = _FENCE_RE.match(line)
        if m and (m.group(1) or "").lower() == "mermaid":
            n += 1
    # every diagram opens and closes; openings == diagrams (odd count = unclosed, still counts)
    return n


def list_docs() -> dict:
    out = []
    for d in _DOCS:
        path = _resolve(d)
        if path is None:
            out.append({**d, "available": False, "diagrams": 0})
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read(MAX_BYTES + 1)
            truncated = len(text) > MAX_BYTES
            out.append({**d, "available": True, "diagrams": _diagram_count(text[:MAX_BYTES]),
                        "truncated": truncated})
        except OSError:
            out.append({**d, "available": False, "diagrams": 0})
    return {"design_dir": DESIGN_DIR, "docs": out,
            "available": any(o.get("available") for o in out)}


def get_doc(doc_id: str) -> dict:
    entry = _entry(doc_id)
    if entry is None:
        raise UnknownDoc(doc_id)
    path = _resolve(entry)
    if path is None:
        raise UnknownDoc(doc_id)
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read(MAX_BYTES + 1)
    truncated = len(text) > MAX_BYTES
    return {"id": doc_id, "title": entry["title"], "group": entry["group"],
            "markdown": text[:MAX_BYTES], "truncated": truncated,
            "diagrams": _diagram_count(text[:MAX_BYTES])}
