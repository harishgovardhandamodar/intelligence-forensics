"""Unit tests for reporter claims-vs-evidence validation (P5.21)."""
from iforensics import claims


def _manifest(**kw):
    m = {"run_id": "r1", "services": ["good", "bad", "ugly"],
         "heuristic_investigation": {
             "good": {"project": "KG extractor",
                      "evidence": {"templates": ["extract structured facts for a knowledge graph"],
                                   "instructions": [], "sample_heads": []}},
             "bad": {"project": "tutor",
                     "evidence": {"templates": ["something else entirely"],
                                  "instructions": [], "sample_heads": []}},
             "ugly": {"project": "x", "evidence": {"templates": [], "instructions": [],
                                                   "sample_heads": []}}},
         "agents": {
             "profilers": {
                 "good": {"parsed": {"project": "KG extractor",
                                     "evidence_quotes": ["extract structured facts"]}},
                 "bad": {"parsed": {"project": "tutor",
                                    "evidence_quotes": ["the moon is made of cheese"]}},
                 "ugly": {"error": "boom"}},
             "critics": {"good": {"content": "- gap: no error handling\n"}},
             "reporter": {"content": "Brief text about findings. Mentions gap work."}},
         "security": {"n_findings": 5, "totals": {}}}
    m.update(kw)
    return m

def test_proven_unproven_and_bad_quote():
    out = claims.validate_run(_manifest())
    assert out["services"]["good"]["proven"] is True
    assert out["services"]["good"]["quotes_verified"] == 1
    bad = out["services"]["bad"]
    assert bad["proven"] is False
    assert bad["unverified_quotes"] == ["the moon is made of cheese"]
    assert out["services"]["ugly"]["issues"] == ["profiler failed or missing",
                                                 "no usable profiler result"]
    assert out["summary"] == {"n_services": 3, "proven": 1, "unproven": 2,
                              "contested": 0, "brief_issues": 1}
    assert out["brief_issues"] == [
        "security findings present but no Security section in brief"]


def test_old_manifest_without_evidence_does_not_false_fail():
    m = _manifest()
    del m["heuristic_investigation"]["good"]["evidence"]
    out = claims.validate_run(m)
    assert out["services"]["good"]["quotes_unverified"] == 1
    assert out["services"]["good"]["proven"] is True  # structural checks pass


def test_empty_and_missing_reporter():
    out = claims.validate_run({})
    assert out["summary"]["n_services"] == 0
    assert out["brief_issues"] == ["no security scan recorded for this run",
                                   "reporter produced no text"]
    m = _manifest()
    m["agents"]["reporter"] = {"content": "## Security posture\nrisk is high. gap closed."}
    out2 = claims.validate_run(m)
    assert out2["brief_issues"] == []


def test_contested_agreement():
    m = _manifest()
    m["agents"]["profilers"]["good"]["parsed"]["project"] = "completely different thing xyz"
    out = claims.validate_run(m)
    assert out["services"]["good"]["agreement"] == "contested"
    assert out["summary"]["contested"] == 1
