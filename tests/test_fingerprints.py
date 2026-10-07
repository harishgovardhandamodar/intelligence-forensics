"""Unit tests for prompt fingerprinting (normalize / template / cluster)."""
from iforensics.fingerprints import (
    normalize,
    template_of,
    signature,
    fingerprint_service,
    extract_instructions,
    extract_schema_hints,
)


def test_normalize_collapses_whitespace_and_truncates():
    p = normalize("  you are\n\ta   helper\ton  projects  ")
    assert p == "you are a helper on projects"
    long = "x" * 500
    assert len(normalize(long)) == 220
    assert normalize(None) == ""


def test_normalize_is_stable_between_calls():
    p = "  Multi-line   prompt   here "
    assert normalize(p) == normalize(p)


def test_template_of_replaces_title_slot():
    p = "You are an analyst.\nTITLE: Recession risk in Web3 lending\nCONTENT: details here"
    t = template_of(p)
    assert "TITLE: {{title}}" in t
    assert "CONTENT: {{content}}" in t
    assert "Recession risk in Web3 lending" not in t


def test_template_of_keeps_fixed_head():
    p = "Always reply in JSON.\nTask: summarize\nMore: lines here"
    t = template_of(p)
    assert t.startswith("Always reply in JSON.")


def test_signature_is_prefix_of_normalize():
    p = "   normalize me   to a short, stable key   "
    assert signature(p) == normalize(p, 120)


def test_fingerprint_service_dedups_and_ranks():
    prompts = [
        "Summarize brief.\nTitle: one\nbody",
        "Summarize brief.\nTitle: two\nbody",
        "Different prompt entirely: this one is longer.\nTitle: three\nbody",
    ] * 3
    fp = fingerprint_service(prompts)
    assert fp["n_prompts"] == 9
    # raw normalised heads differ (Title: value sits inside the head)
    assert fp["n_clusters"] == 3
    # ...but the slot-identical templates collapse to 2
    assert len(fp["templates"]) == 2
    assert fp["templates"][0]["count"] == 6
    assert fp["templates"][0]["template"].startswith("Summarize brief.")


def test_fingerprint_service_empty():
    fp = fingerprint_service([])
    assert fp["n_prompts"] == 0
    assert fp["templates"] == []


def test_extract_instructions_filters_by_shape():
    prompts = [
        "You are a researcher.\nExtract key findings from the paper.\nthis is too short\n",
        "Produce a concise digest of the brief.\n{n}. Record the exposure tier.\n",
        "Write a short title for the subject.\n",
    ]
    got = extract_instructions(prompts, max_items=10)
    assert len(got) >= 3
    assert any("Extract key findings" in g for g in got)
    assert len(got) <= 10


def test_extract_instructions_dedup():
    p = ["You are a robot.\nProduce a concise digest of the brief.\n",
         "You are a robot.\nProduce a concise digest of the brief.\n",
         "Inject this too.\nDo not include any of that.\n"]
    got = extract_instructions(p, max_items=10)
    assert len(set(g.lower() for g in got)) == len(got)


def test_extract_schema_hints_keywords():
    prompts = ["This is a knowledge graph service for knowledge graph stuff.",
               "Output schema: structured facts with Title/content.",
               "Nothing here."]
    hints = extract_schema_hints(prompts)
    assert "knowledge graph" in hints
    assert "structured facts" in hints or "title/content" in hints
    assert hints == sorted(hints)