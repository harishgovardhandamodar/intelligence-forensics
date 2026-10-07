"""Unit tests for the reconstruction-score / vibe-index heuristics.

These are the two transparency numbers shown in the UI; their behavior
(ceilings, grades, labels, monotonicity) is locked here so a future refactor
cannot silently change what a user is being told about a service.
"""
import math

from iforensics.score import grade, score_profile, vibe_index, attach_scores


def test_grade_bounds():
    assert grade(100) == "A"
    assert grade(80) == "A"
    assert grade(79.9) == "B"
    assert grade(65) == "B"
    assert grade(50) == "C"
    assert grade(49.9) == "D"
    assert grade(0) == "D"


def test_score_profile_empty_first_step_is_stability_only():
    r = score_profile({"requests": 0, "fingerprint": {"templates": []}})
    assert r["score"] == 12.0
    assert r["grade"] == "D"
    assert r["factors"]["volume"] == 0.0
    assert r["factors"]["stability"] == 12.0


def test_score_profile_first_step_stability():
    profile = {
        "requests": 10,
        "models": {"m": 10},
        "project": "p",
        "fingerprint": {"templates": [{"t": 1}, {"t": 2}]},
        "instructions": ["a", "b", "c"],
        "schema_hints": ["schema", "brief"],
    }
    r = score_profile(profile)  # prev_project=None -> stability 12
    assert r["factors"]["stability"] == 12.0
    assert r["factors"]["volume"] == round(min(25.0, 8 * math.log10(11)), 1)
    assert r["factors"]["templates"] == 8.0
    assert r["factors"]["instructions"] == 9.0
    assert r["factors"]["schema"] == 5.0
    assert r["factors"]["model_focus"] == 10.0
    assert 0 <= r["score"] <= 100.0


def test_score_profile_stability_penalty_on_project_flip():
    profile = {"requests": 1, "project": "B", "models": {"m": 1}}
    stable = score_profile({**profile, "project": "A"}, prev_project="A")
    assert stable["factors"]["stability"] == 20.0
    flipped = score_profile(profile, prev_project="A")
    assert flipped["factors"]["stability"] == 5.0


def test_score_ceiling_single_model():
    big = {"requests": 1_000_000, "project": "p",
           "models": {"m": 99},
           "fingerprint": {"templates": [{"t": i} for i in range(50)]},
           "instructions": ["i"] * 50, "schema_hints": ["s"] * 50}
    r = score_profile(big, prev_project="p")
    assert r["score"] == 100.0
    assert r["grade"] == "A"


def test_vibe_share_model_focus():
    r = vibe_index({"requests": 100, "models": {"a": 90, "b": 10},
                    "fingerprint": {"templates": [{"t": 1}]},
                    "instructions": ["i"] * 4, "pipeline": ["a", "b"]})
    assert r["factors"]["focus"] == 18.0
    assert r["label"] in ("pure vibe", "hybrid", "engineered system")


def test_vibe_multi_model_staged_system_is_engineered():
    four_models = {"a": 5, "b": 5, "c": 5, "d": 5}  # 25% share each
    r = vibe_index({"requests": 50, "models": four_models,
                    "fingerprint": {"templates": [{"t": i} for i in range(6)]},
                    "instructions": [], "pipeline": ["s%d" % i for i in range(8)]})
    assert r["label"] == "engineered system"
    assert r["factors"]["focus"] < 10
    assert r["factors"]["simplicity"] == 0.0


def test_vibe_more_stages_never_raises_total():
    base = {"requests": 200, "models": {"m": 1},
            "fingerprint": {"templates": [{"t": i} for i in range(4)]},
            "instructions": ["i"] * 2}
    few = vibe_index({**base, "pipeline": ["a", "b"]}, stable=True)
    many = vibe_index({**base, "pipeline": ["s%d" % i for i in range(8)]}, stable=True)
    assert many["factors"]["simplicity"] < few["factors"]["simplicity"]
    assert many["vibe"] <= few["vibe"]


def test_vibe_steadiness():
    assert vibe_index({}, stable=True)["factors"]["steadiness"] == 15.0
    assert vibe_index({}, stable=False)["factors"]["steadiness"] == 5.0
    assert vibe_index({})["factors"]["steadiness"] == 10.0


def test_attach_scores_mutates_steps_in_place():
    prog = {"steps": [
        {"requests": 4, "models": {"m": 4}, "project": "A", "pipeline": ["x"],
         "n_templates": 1, "n_instructions": 1, "schema_hints": ["s"]},
        {"requests": 4, "models": {"m": 4}, "project": "A", "pipeline": ["x"],
         "n_templates": 2, "n_instructions": 2, "schema_hints": ["s"]},
    ]}
    attach_scores(prog, rows_by_service=None)
    assert "score" in prog["steps"][0] and "vibe" in prog["steps"][0]
    assert prog["steps"][0]["score"]["factors"]["volume"] == round(8 * math.log10(5), 1)