"""Per-run sim dossier (AKM dossier structure, adapted).

Mirrors the agentic-knowledge-mapper investigation dossier the way it
mirrors everything else here: same section questions, same rule that every
number traces to a stored row. Sections:

  §0 The request — scenarios, params, DLP mode, timestamp (verbatim inputs)
  §1 What ran — per scenario: user, turns, style, DLP interceptions, attack
      stats, cluster counts
  §2 What was collected — embedding counts, per-user pairs, backend
  §3 Findings — per field: verdict band, accuracy, direct-exposure flag,
      reconstructed value + coverage/occurrences, membership true-vs-fresh
  §4 How each score was derived — matched/total chars per field, curve
      points, membership scores, estimate-vs-actual deltas
  §5 Ledger timeline — the run's hash-chained entries in order + verify state
  §6 Plausibility verdict

`build_dossier` returns the structured dict; `dossier_markdown` renders it
with the same tables-and-headings voice as the security brief.
"""
from __future__ import annotations

from .analysis import char_accuracy


def _band(acc: float, direct: bool) -> str:
    if direct:
        return "critical"
    if acc >= 1.0:
        return "critical"
    if acc >= 0.5:
        return "high"
    if acc > 0.0:
        return "medium"
    return "low"


def build_dossier(run_id: str, results: dict, ledger_entries: list[dict],
                  verify: dict) -> dict:
    """Assemble the dossier from persisted scenario results + ledger trail."""
    scenarios = {}
    findings = []
    for name, r in (results or {}).items():
        if not isinstance(r, dict) or "report" not in r:
            scenarios[name] = {"error": r.get("error", "no report") if isinstance(r, dict) else "no report"}
            continue
        rep = r["report"]
        truth = r.get("truth") or {}
        cands = rep.get("reconstructed") or []
        fields = {}
        for field, fr in (rep.get("fields") or {}).items():
            band = _band(fr.get("accuracy", 0.0), bool(fr.get("direct_exposure")))
            tv = truth.get(field, "")
            # the assembly attributable to THIS field: best positional match
            # against its truth (falls back to top assembly without truth)
            best_asm, best_acc = "", -1.0
            for s in cands:
                a = char_accuracy(s.get("assembled", ""), tv)["accuracy"] \
                    if tv else -1.0
                if a > best_acc:
                    best_acc, best_asm = a, s.get("assembled", "")
            if not tv and cands:
                best_asm = cands[0].get("assembled", "")
            fields[field] = {
                "accuracy": fr.get("accuracy"), "matched": fr.get("matched"),
                "total": fr.get("total"), "recovered": fr.get("recovered"),
                "direct_exposure": bool(fr.get("direct_exposure")),
                "band": band,
                "curve": rep.get("curves", {}).get(field, []),
            }
            findings.append({"scenario": name, "field": field, "band": band,
                             "accuracy": fr.get("accuracy"),
                             "direct_exposure": bool(fr.get("direct_exposure")),
                             "reconstructed": best_asm})
        est = rep.get("estimates") or {}
        scenarios[name] = {
            "user_id": r.get("user_id"), "n_turns": r.get("n_turns"),
            "style": r.get("style", "regular"),
            "attack": r.get("attack", {}),
            "membership": r.get("membership", {}),
            "dlp": rep.get("dlp", {}),
            "estimates": {"exposure": est.get("exposure"),
                          "n_groups": est.get("n_groups")},
            "fields": fields,
            "summary": {"recovered": rep.get("recovered"),
                        "n_fields": rep.get("n_fields"),
                        "mean_accuracy": rep.get("mean_accuracy")},
        }
    findings.sort(key=lambda f: ({"critical": 0, "high": 1, "medium": 2,
                                  "low": 3}[f["band"]], f["scenario"], f["field"]))
    timeline = [{"seq": e.get("seq"), "actor": e.get("actor"),
                 "action": e.get("action"), "task_id": e.get("task_id") or "",
                 "artifact_sha": (e.get("artifact_sha256") or "")[:12],
                 "detail": e.get("detail") or ""} for e in ledger_entries]
    return {"run_id": run_id, "scenarios": scenarios, "findings": findings,
            "timeline": timeline,
            "ledger": {"ok": bool(verify.get("ok")),
                       "checked": verify.get("checked", 0),
                       "failed_at": verify.get("failed_at")}}


def dossier_markdown(d: dict) -> str:
    """Render the dossier as Markdown (tables + headings, no new deps)."""
    L = [f"# Sim dossier — run `{d['run_id']}`", ""]
    L += ["## §0 Request", ""]
    for name, s in d["scenarios"].items():
        if "error" in s:
            L.append(f"- **{name}**: error — {s['error']}")
            continue
        dlp = (s.get("dlp") or {})
        L.append(f"- **{name}** (style {s.get('style')}, "
                 f"{s.get('n_turns')} turns, user `{s.get('user_id')}`, "
                 f"DLP {dlp.get('mode', 'off')})")
    L += ["", "## §1 Findings", "",
          "| band | scenario | field | accuracy | direct | reconstructed |",
          "|---|---|---|---|---|---|"]
    for f in d["findings"]:
        L.append(f"| {f['band']} | {f['scenario']} | {f['field']} | "
                 f"{f['accuracy']} | {'yes' if f['direct_exposure'] else 'no'} | "
                 f"`{f['reconstructed']}` |")
    if not d["findings"]:
        L.append("| — | no findings | — | — | — | — |")
    L += ["", "## §2 Scores derived", ""]
    for name, s in d["scenarios"].items():
        if "error" in s:
            continue
        L.append(f"### {name}")
        for field, fr in s["fields"].items():
            curve = ",".join(str(p.get("accuracy")) for p in fr.get("curve", []))
            L.append(f"- `{field}`: {fr['matched']}/{fr['total']} chars "
                     f"(curve [{curve}])")
        for field, m in (s.get("membership") or {}).items():
            L.append(f"- membership `{field}`: true={m.get('true_score')} "
                     f"fresh={m.get('fresh_score')} "
                     f"({'member' if m.get('likely_member') else 'unclear'})")
        L.append(f"- exposure estimate: {s.get('estimates', {}).get('exposure')} "
                 f"over {s.get('estimates', {}).get('n_groups')} groups; "
                 f"clusters: {s.get('attack', {}).get('n_clusters')}; "
                 f"DLP interceptions: {(s.get('dlp') or {}).get('interceptions', 0)}")
    L += ["", "## §3 Ledger timeline", ""]
    lg = d["ledger"]
    L.append(f"_chain {'OK' if lg['ok'] else 'BROKEN'} — "
             f"{lg['checked']} entries"
             + ("" if lg["ok"] else f", failed at seq {lg['failed_at']}"))
    L += ["", "| seq | actor | action | task | artifact | detail |",
          "|---|---|---|---|---|---|"]
    for e in d["timeline"]:
        L.append(f"| {e['seq']} | {e['actor']} | {e['action']} | {e['task_id']} | "
                 f"`{e['artifact_sha']}` | {e['detail']} |")
    if not d["timeline"]:
        L.append("| — | no entries | — | — | — | — |")
    return "\n".join(L) + "\n"
