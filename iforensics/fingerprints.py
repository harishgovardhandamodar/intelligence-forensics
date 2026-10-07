"""Prompt fingerprinting: cluster raw prompts into stable templates per service.

Goal: from N raw (possibly truncated/masked) prompts, recover the *code* that
generated them — i.e. the system-prompt template + slot names.
"""
import re
from collections import Counter

_WS = re.compile(r"\s+")
_SLOT_PATTERNS = [
    (re.compile(r"TITLE:\s*.*", re.S), "TITLE: {{title}}"),
    (re.compile(r"CONTENT:\s*.*", re.S), "CONTENT: {{content}}"),
    (re.compile(r"Brief:\s*.*", re.S), "Brief: {{brief}}"),
    (re.compile(r"Product:\s*.*", re.S), "Product: {{product}}"),
    (re.compile(r"Model:\s*.*", re.S), "Model: {{model_desc}}"),
    (re.compile(r"Title:\s*.*", re.S), "Title: {{paper_title}}"),
    (re.compile(r"Paper:\s*.*", re.S), "Paper: {{paper}}"),
    (re.compile(r"Subject:\s*.*", re.S), "Subject: {{subject}}"),
    (re.compile(r"Skill:\s*.*", re.S), "Skill: {{skill}}"),
    (re.compile(r"Task:\s*.*", re.S), "Task: {{task}}"),
    (re.compile(r"Context:\s*.*", re.S), "Context: {{context}}"),
]


def normalize(prompt: str, head_len: int = 220) -> str:
    p = _WS.sub(" ", (prompt or "").strip())
    return p[:head_len]


def template_of(prompt: str) -> str:
    """Replace variable slots with {{placeholders}} to reveal the fixed template."""
    p = (prompt or "").strip()
    # cut to template head: keep first ~600 chars then slot-ify
    head = p[:800]
    for rx, repl in _SLOT_PATTERNS:
        head = rx.sub(repl, head, count=1)
    return head


def signature(prompt: str) -> str:
    """Stable cluster key: first 120 normalized chars (template head, pre-slot)."""
    return normalize(prompt, 120)


def fingerprint_service(prompts: list[str], max_templates: int = 6) -> dict:
    sigs = Counter(signature(p) for p in prompts if p)
    templates: dict[str, dict] = {}
    for sig, count in sigs.most_common(max_templates * 3):
        example = next((p for p in prompts if signature(p) == sig), "")
        tpl = template_of(example)
        key = tpl[:200]
        if key not in templates:
            templates[key] = {"count": 0, "template": tpl, "example_head": example[:500]}
        templates[key]["count"] += count
    ranked = sorted(templates.values(), key=lambda t: -t["count"])[:max_templates]
    return {
        "n_prompts": len(prompts),
        "n_clusters": len(sigs),
        "top_signatures": [{"sig": s, "count": c} for s, c in sigs.most_common(10)],
        "templates": ranked,
    }


def extract_instructions(prompts: list[str], max_items: int = 10) -> list[str]:
    """Pull imperative instruction sentences (the 'spec' the builder coded)."""
    found: list[str] = []
    seen: set[str] = set()
    for p in prompts:
        for line in (p or "").split("\n"):
            s = line.strip(" -•*").strip()
            if len(s) < 20 or len(s) > 300:
                continue
            if re.match(r"(?i)^(you are|based only|do not|produce|extract|write|cover|enumerate|be |title:|brief:|product:|model:|subject:|task:)", s):
                if s[:80].lower() not in seen:
                    seen.add(s[:80].lower())
                    found.append(s)
            if len(found) >= max_items:
                return found
    return found


def extract_schema_hints(prompts: list[str]) -> list[str]:
    hints: set[str] = set()
    for p in prompts:
        pl = (p or "").lower()
        for kw in ("knowledge graph", "structured facts", "schema", "title/content",
                    "exposure tier", "residual risk", "misuse potential", "model risk",
                    "brief", "digest", "implications for quai", "what to watch",
                    "abstract", "figures available", "experimental setup", "research questions",
                    "subject:", "skill:", "tutor", "check question", "guiding question"):
            if kw in pl:
                hints.add(kw)
    return sorted(hints)
