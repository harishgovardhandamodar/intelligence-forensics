"""Investigator: turn fingerprints + traffic stats into 'what are they building'.

Each ServiceProfile answers: purpose, pipeline stages, I/O schema, models,
cadence — all with row counts as evidence, so claims are checkable.
"""
from collections import Counter
from . import fingerprints as fp

# heuristic purpose detectors: keyword -> (project_label, purpose, pipeline)
_RULES = [
    (("knowledge graph", "structured facts", "title:", "content:"),
     "blockchain-news knowledge-graph extractor",
     "ingests news items (title+content) -> LLM extracts structured KG facts -> writes graph nodes/edges",
     ["ingest_feed", "build_kg_prompt(title, content)", "llm.extract(model)", "parse_facts", "upsert_graph"]),
    (("what's new", "implications for quai", "what to watch", "research brief"),
     "daily research-brief writer (Quai dashboard)",
     "digest of landscape/news/market -> brief prompt -> concise markdown brief (whats-new/implications/watch)",
     ["build_digest", "render_brief_prompt", "llm.summarize(model)", "publish_dashboard"]),
    (("exposure tier", "residual risk", "model risk", "misuse potential", "in-app evidence"),
     "multi-agent debate risk scorer",
     "brief/product/model descriptors -> risk-scoring prompts (tiers 0-100, CVE/attack mapping) -> risk register",
     ["make_brief", "score_product_risk", "score_model_risk", "map_attacks(CVE)", "emit_register"]),
    (("brief:", "failure modes", "sycophancy", "collusion"),
     "multi-agent debate research synthesizer",
     "topic briefs -> literature-synthesis prompts (architectures/benchmarks/risks) -> reports",
     ["make_topic_brief", "synthesize_architectures", "synthesize_risks", "write_report"]),
    (("abstract", "experimental setup", "research questions", "figures available"),
     "paper-surrogate / research-paper summarizer",
     "paper sections (abstract/figures/experiments) -> section-wise summarization prompts -> surrogates/summaries",
     ["extract_sections", "summarize_section(model)", "summarize_figures", "build_surrogate"]),
    (("subject:", "skill:", "tutor", "check question", "guiding question"),
     "tutor / learning-lab skill coach",
     "skill+learner-state -> pedagogical prompts (teach/clue/investigate/challenge) -> tutor turn",
     ["learner_state", "render_skill_prompt", "llm.coach(embed_model|chat)", "next_step"]),
]


def infer_purpose(prompts: list[str], service: str) -> dict:
    blobs = " || ".join((p or "")[:400].lower() for p in prompts[:50])
    best = None
    best_hits = 0
    for kws, label, purpose, pipeline in _RULES:
        hits = sum(1 for k in kws if k in blobs)
        if hits > best_hits:
            best_hits = hits
            best = (label, purpose, pipeline)
    if best and best_hits >= 2:
        return {"project": best[0], "pipeline_summary": best[1], "pipeline": best[2], "rule_hits": best_hits}
    # fallback: generic per-service label
    return {"project": f"{service} workload (unclassified)",
            "pipeline_summary": "prompts -> LLM -> unknown sink (needs more samples)",
            "pipeline": ["capture_prompt", "llm.call(model)", "unknown_sink"],
            "rule_hits": best_hits}


def profile_service(service: str, rows: list[dict]) -> dict:
    prompts = [r.get("prompt") or "" for r in rows if r.get("prompt")]
    models = Counter(r.get("model") or "unknown" for r in rows)
    qtypes = Counter(r.get("query_type") or "(none)" for r in rows)
    reqs = Counter(r.get("requestor") or "user" for r in rows)
    statuses = Counter(r.get("status") or "?" for r in rows)
    toks = sum((r.get("total_tokens") or 0) for r in rows)
    ts = sorted(r.get("ts", 0) for r in rows if r.get("ts"))
    cadence_s = (ts[-1] - ts[0]) / max(1, len(ts) - 1) if len(ts) > 1 else 0
    fing = fp.fingerprint_service(prompts)
    purpose = infer_purpose(prompts, service)
    return {
        "service": service,
        "requests": len(rows),
        "total_tokens": toks,
        "avg_tokens": round(toks / len(rows), 1) if rows else 0,
        "models": dict(models.most_common()),
        "query_types": dict(qtypes.most_common()),
        "requestors": dict(reqs),
        "statuses": dict(statuses),
        "cadence_median_s": round(cadence_s, 1),
        "time_range": [ts[0], ts[-1]] if ts else [],
        **purpose,
        "schema_hints": fp.extract_schema_hints(prompts),
        "instructions": fp.extract_instructions(prompts),
        "fingerprint": fing,
        "sample_heads": [p[:300].replace("\n", " | ") for p in prompts[:3]],
    }


def investigate_all(rows: list[dict], min_requests: int = 1) -> dict:
    by_svc: dict[str, list[dict]] = {}
    for r in rows:
        by_svc.setdefault(r.get("service") or "unknown", []).append(r)
    profiles = {}
    for svc, rs in sorted(by_svc.items(), key=lambda kv: -len(kv[1])):
        if len(rs) >= min_requests:
            profiles[svc] = profile_service(svc, rs)
    return {"n_services": len(profiles), "n_requests": len(rows), "services": profiles}
