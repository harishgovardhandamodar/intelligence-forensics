"""gateway-unknown — RECONSTRUCTED from fox-services LLM telemetry.
Source: intelligence-forensics evidence (21 requests, {"nomic-embed-text:latest": 10, "qwen3.8:latest": 5, "unknown": 2, "llama3.2:3b": 2, "qwen3.8:27b": 1, "gemma4:31b": 1}).
This scaffold reproduces the OBSERVED behavior: prompt templates, pipeline
stages and model calls. Fill in sinks marked TODO with the real destination
(DB/graph/dashboard) to get a functional clone.
"""
import os
import urllib.request
import json

FOX_URL = os.environ.get("FOX_URL", "http://localhost:8210")
SERVICE = "gateway-unknown"
MODEL = "nomic-embed-text:latest"

PROMPT_TEMPLATES = {
  "template_1": "hi",
  "template_2": "say hi",
  "template_3": "Reply with the single word: ready"
}

def call_llm(prompt: str, model: str = MODEL) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}).encode()
    req = urllib.request.Request(
        FOX_URL + "/api/chat", data=body,
        headers={"Content-Type": "application/json", "X-Service-Name": SERVICE},
        method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

def capture_prompt(item: dict) -> dict:
    """Stage `capture_prompt` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def llm_call_model(item: dict) -> dict:
    """Stage `llm.call(model)` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def unknown_sink(item: dict) -> dict:
    """Stage `unknown_sink` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


STAGES = {
    "capture_prompt": capture_prompt,
    "llm.call(model)": llm_call_model,
    "unknown_sink": unknown_sink,
}


def run_once(inputs: list[dict]) -> list[dict]:
    """inputs: list of slot dicts matching the templates above."""
    out = []
    for item in inputs:
        out.append({stage: stage_fn(item) for stage, stage_fn in STAGES.items()})
    return out

if __name__ == "__main__":
    print(f"{SERVICE} reconstructed scaffold: {len(PROMPT_TEMPLATES)} templates, stages={list(STAGES)}")
