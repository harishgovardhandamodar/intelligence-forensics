"""agentic-knowledge-mapper — RECONSTRUCTED from fox-services LLM telemetry.
Source: intelligence-forensics evidence (1207 requests, {"qwen3.8:27b": 967, "qwen3.8:latest": 130, "nomic-embed-text:latest": 109, "gemma4:31b": 1}).
This scaffold reproduces the OBSERVED behavior: prompt templates, pipeline
stages and model calls. Fill in sinks marked TODO with the real destination
(DB/graph/dashboard) to get a functional clone.
"""
import os
import urllib.request
import json

FOX_URL = os.environ.get("FOX_URL", "http://localhost:8210")
SERVICE = "agentic-knowledge-mapper"
MODEL = "qwen3.8:27b"

PROMPT_TEMPLATES = {
  "template_1": "Model: {{model_desc}}",
  "template_2": "Brief: {{brief}}",
  "template_3": "Product: {{product}}",
  "template_4": "Question: what level of memorization by these network is plausible, what would be the closest reconstruction plausible ? is it possible to use this synthetic data by a party who has major share in data trained to reconstruct other party's data sample or population? what are the methods to evaluate the yield of synthetic data with respect to Privacy, Utility and fidelity?\n\nSources:\n[0] SoK: Reconstruction Attacks on Synthetic Tabular Data (Insights from ...: Full PDF of the SoK paper systematical"
}

def call_llm(prompt: str, model: str = MODEL) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}).encode()
    req = urllib.request.Request(
        FOX_URL + "/api/chat", data=body,
        headers={"Content-Type": "application/json", "X-Service-Name": SERVICE},
        method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

def make_brief(item: dict) -> dict:
    """Stage `make_brief` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def score_product_risk(item: dict) -> dict:
    """Stage `score_product_risk` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def score_model_risk(item: dict) -> dict:
    """Stage `score_model_risk` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def map_attacks_CVE(item: dict) -> dict:
    """Stage `map_attacks(CVE)` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def emit_register(item: dict) -> dict:
    """Stage `emit_register` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


STAGES = {
    "make_brief": make_brief,
    "score_product_risk": score_product_risk,
    "score_model_risk": score_model_risk,
    "map_attacks(CVE)": map_attacks_CVE,
    "emit_register": emit_register,
}


def run_once(inputs: list[dict]) -> list[dict]:
    """inputs: list of slot dicts matching the templates above."""
    out = []
    for item in inputs:
        out.append({stage: stage_fn(item) for stage, stage_fn in STAGES.items()})
    return out

if __name__ == "__main__":
    print(f"{SERVICE} reconstructed scaffold: {len(PROMPT_TEMPLATES)} templates, stages={list(STAGES)}")
