"""Scoring for reconstructions: HOW WELL can we rebuild this app from logs?

Two transparent 0-100 heuristics (no LLM, fully explainable):

reconstruction score — evidence strength behind the inferred codebase:
  volume            0-25  8*log10(1+requests)          (more queries = more proof)
  template richness 0-20  4 * n_templates             (recovered prompt surface)
  instruction signal 0-15 3 * n_instructions          (recovered spec sentences)
  schema clarity    0-10  2.5 * n_schema_hints        (known I/O vocabulary)
  model focus       0-10  10 * top_model_share         (single-model = clearer calls)
  label stability   0-20  20 stable / 5 flipped / 12 first step

vibe index — how much the app looks like a PURE VIBE-CODED thin prompt
wrapper (copy-pasted prompts, one model, no visible engineering) vs an
engineered system (many templates, multi-model, staged pipeline):
  reuse      0-30  10*log10(1 + requests/max(1,n_templates))
  focus      0-20  20 * top_model_share
  simplicity 0-20  20 * (1 - min(1, n_stages/8))
  spec       0-15  15 * min(1, n_instructions/4)   (behavior lives in prose prompts)
  steadiness 0-15  15 stable / 5 flipped / 10 first step
Labels: >=70 "pure vibe" · 40-70 "hybrid" · <40 "engineered system".
"""
import math

GRADES = ((80, "A"), (65, "B"), (50, "C"), (0, "D"))


def grade(score: float) -> str:
    for bound, g in GRADES:
        if score >= bound:
            return g
    return "D"


def _shares(models: dict) -> float:
    tot = sum(models.values()) if models else 0
    return (max(models.values()) / tot) if tot else 0.0


def score_profile(profile: dict, prev_project: str | None = None) -> dict:
    reqs = profile.get("requests", 0) or 0
    tpls = profile.get("fingerprint", {}).get("templates", []) or []
    n_tpl, n_ins = len(tpls), len(profile.get("instructions") or [])
    n_hints = len(profile.get("schema_hints") or [])
    share = _shares(profile.get("models") or {})
    if prev_project is None:
        stability = 12.0
    else:
        stability = 20.0 if profile.get("project") == prev_project else 5.0

    factors = {
        "volume": round(min(25.0, 8 * math.log10(1 + reqs)), 1),
        "templates": round(min(20.0, 4 * n_tpl), 1),
        "instructions": round(min(15.0, 3 * n_ins), 1),
        "schema": round(min(10.0, 2.5 * n_hints), 1),
        "model_focus": round(10 * share, 1),
        "stability": stability,
    }
    total = round(min(100.0, sum(factors.values())), 1)
    return {"score": total, "grade": grade(total), "factors": factors}


def vibe_index(profile: dict, stable: bool | None = None) -> dict:
    reqs = profile.get("requests", 0) or 0
    tpls = profile.get("fingerprint", {}).get("templates", []) or []
    n_tpl = max(1, len(tpls))
    share = _shares(profile.get("models") or {})
    n_stages = len(profile.get("pipeline") or [])
    n_ins = len(profile.get("instructions") or [])
    steadiness = 10.0 if stable is None else (15.0 if stable else 5.0)
    factors = {
        "reuse": round(min(30.0, 10 * math.log10(1 + reqs / n_tpl)), 1),
        "focus": round(20 * share, 1),
        "simplicity": round(20 * (1 - min(1.0, n_stages / 8)), 1),
        "spec": round(15 * min(1.0, n_ins / 4), 1),
        "steadiness": steadiness,
    }
    total = round(min(100.0, sum(factors.values())), 1)
    label = "pure vibe" if total >= 70 else ("hybrid" if total >= 40 else "engineered system")
    return {"vibe": total, "label": label, "factors": factors}


def attach_scores(prog: dict, rows_by_service: dict | None = None) -> dict:
    """Enrich a progression() result in place: per-step score + vibe + verdict."""
    prev_project: str | None = None
    for st in prog.get("steps", []):
        # score_* only read COUNTS from these lists, so length-correct stubs suffice
        pseudo = {"requests": st["requests"], "models": st.get("models", {}),
                  "project": st["project"], "pipeline": st.get("pipeline", []),
                  "schema_hints": ["h"] * len(st.get("schema_hints", [])),
                  "instructions": ["i"] * (st.get("n_instructions", 0) or 0),
                  "fingerprint": {"templates": [{}] * (st.get("n_templates", 0) or 0)}}
        st["score"] = score_profile(pseudo, prev_project)
        st["vibe"] = vibe_index(pseudo,
                                stable=None if prev_project is None
                                else (st["project"] == prev_project))
        prev_project = st["project"]
    return prog
