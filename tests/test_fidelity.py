"""Unit tests for reconstruction fidelity scoring (P5.20)."""
import os

from iforensics import fidelity as fid


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _seed(base):
    _write(os.path.join(base, "svc", "prompts", "template_1.txt"),
           "Summarise the following build log in three bullet points.\n\n"
           "--- EXAMPLE HEAD ---\nSummarise the following build log ... output text")
    _write(os.path.join(base, "svc", "prompts", "template_2.txt"),
           "Translate the following error message into French and explain the cause.")


def test_match_and_drift(tmp_path):
    _seed(str(tmp_path))
    tpls = fid.load_templates("svc", recon_dir=str(tmp_path))
    assert [t["name"] for t in tpls] == ["template_1.txt", "template_2.txt"]
    # example-head text must not leak into the matchable template
    assert "EXAMPLE HEAD" not in tpls[0]["text"]
    prompts = ["Please summarise the following build log in three bullet points:\nlog...",
               "Something completely unrelated about cooking pasta."]
    out = fid.score_service("svc", prompts, templates=tpls)
    assert out["matched"] == 1 and out["match_rate"] == 0.5
    assert out["verdict"] == "drifting"
    assert out["drifted"] == ["template_2.txt"]


def test_fresh_and_stale_verdicts():
    tpls = [{"name": "t1", "text": "x" * 60, "shingles": fid._shingles("x" * 60)}]
    many = ["y " * 40 for _ in range(5)]
    assert fid.score_service("s", many, templates=tpls)["verdict"] == "stale"
    same = [" ".join(["x"] * 60) for _ in range(5)]
    # single-word template has < MIN_SHINGLES distinct shingles -> never matches
    assert fid.score_service("s", same, templates=tpls)["matched"] == 0


def test_empty_cases():
    assert fid.score_service("s", ["hi"], templates=[])["verdict"] == "no-templates"
    tpls = [{"name": "t1", "text": "some template text here", "shingles": frozenset({"a"})}]
    assert fid.score_service("s", [], templates=tpls)["verdict"] == "no-traffic"
    assert fid.load_templates("missing", recon_dir="/nonexistent") == []


def test_score_all_ranks_worst_first(tmp_path):
    shared = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    _write(os.path.join(str(tmp_path), "good", "prompts", "t1.txt"), shared)
    _write(os.path.join(str(tmp_path), "bad", "prompts", "t1.txt"), shared)
    rows = [{"service": "good", "prompt": shared + " plus extra context words here"},
            {"service": "bad", "prompt": "totally unrelated words about cooking"}]
    out = fid.score_all(rows, recon_dir=str(tmp_path))
    assert [s["service"] for s in out["services"]] == ["bad", "good"]
    assert out["summary"] == {"n_services": 2, "fresh": 1,
                              "drifting": 0, "stale": 1}
