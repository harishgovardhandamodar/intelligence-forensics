"""hive-research-gpu — RECONSTRUCTED from fox-services LLM telemetry.
Source: intelligence-forensics evidence (277 requests, {"nomic-embed-text:latest": 227, "llama3.2:3b": 38, "qwen3.8:27b": 12}).
This scaffold reproduces the OBSERVED behavior: prompt templates, pipeline
stages and model calls. Fill in sinks marked TODO with the real destination
(DB/graph/dashboard) to get a functional clone.
"""
import os
import urllib.request
import json

FOX_URL = os.environ.get("FOX_URL", "http://localhost:8210")
SERVICE = "hive-research-gpu"
MODEL = "nomic-embed-text:latest"

PROMPT_TEMPLATES = {
  "template_1": "Title: {{paper_title}}",
  "template_2": "Paper: {{paper}}",
  "template_3": "Answer using ONLY the numbered context excerpts provided. Cite every claim with its excerpt number like [1] or [2][5]. If the context is insufficient, say exactly what is missing instead of guessing.\n\nWrite a thorough research briefing on: Summarize the state of multi-agent debate methods\nStructure: Key findings / Method landscape / Open problems / What your library does not yet cover. Cite as [n].\n\nContext: {{context}}",
  "template_4": "You drafted a partial research answer. List up to 3 specific information gaps as refined arXiv-style search queries. Return JSON: {\"queries\": [\"...\"]}\n\nQuestion: Summarize the state of multi-agent debate methods\nDraft:",
  "template_5": "First write 'Reasoning:' followed by short numbered reasoning steps. Then write 'Answer:' with the final response.\nContext: {{context}}",
  "template_6": "Break this research question into up to 5 focused sub-questions that together cover it. Return JSON: {\"sub_questions\": [\"...\"]}\n\nQuestion: Summarize the state of multi-agent debate methods"
}

def call_llm(prompt: str, model: str = MODEL) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}).encode()
    req = urllib.request.Request(
        FOX_URL + "/api/chat", data=body,
        headers={"Content-Type": "application/json", "X-Service-Name": SERVICE},
        method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

def extract_sections(item: dict) -> dict:
    """Stage `extract_sections` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def summarize_section_model(item: dict) -> dict:
    """Stage `summarize_section(model)` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def summarize_figures(item: dict) -> dict:
    """Stage `summarize_figures` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def build_surrogate(item: dict) -> dict:
    """Stage `build_surrogate` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


STAGES = {
    "extract_sections": extract_sections,
    "summarize_section(model)": summarize_section_model,
    "summarize_figures": summarize_figures,
    "build_surrogate": build_surrogate,
}


def run_once(inputs: list[dict]) -> list[dict]:
    """inputs: list of slot dicts matching the templates above."""
    out = []
    for item in inputs:
        out.append({stage: stage_fn(item) for stage, stage_fn in STAGES.items()})
    return out

if __name__ == "__main__":
    print(f"{SERVICE} reconstructed scaffold: {len(PROMPT_TEMPLATES)} templates, stages={list(STAGES)}")
