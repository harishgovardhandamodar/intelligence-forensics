"""kid-learning-lab — RECONSTRUCTED from fox-services LLM telemetry.
Source: intelligence-forensics evidence (37 requests, {"nomic-embed-text:latest": 32, "gemma4:31b": 5}).
This scaffold reproduces the OBSERVED behavior: prompt templates, pipeline
stages and model calls. Fill in sinks marked TODO with the real destination
(DB/graph/dashboard) to get a functional clone.
"""
import os
import urllib.request
import json

FOX_URL = os.environ.get("FOX_URL", "http://localhost:8210")
SERVICE = "kid-learning-lab"
MODEL = "nomic-embed-text:latest"

PROMPT_TEMPLATES = {
  "template_1": "Subject: {{subject}}",
  "template_2": "Give one short hint about fractions without giving the answer.",
  "template_3": "Say hi in five words.",
  "template_4": "hi"
}

def call_llm(prompt: str, model: str = MODEL) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}).encode()
    req = urllib.request.Request(
        FOX_URL + "/api/chat", data=body,
        headers={"Content-Type": "application/json", "X-Service-Name": SERVICE},
        method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

def learner_state(item: dict) -> dict:
    """Stage `learner_state` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def render_skill_prompt(item: dict) -> dict:
    """Stage `render_skill_prompt` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def llm_coach_embed_model_chat(item: dict) -> dict:
    """Stage `llm.coach(embed_model|chat)` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def next_step(item: dict) -> dict:
    """Stage `next_step` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


STAGES = {
    "learner_state": learner_state,
    "render_skill_prompt": render_skill_prompt,
    "llm.coach(embed_model|chat)": llm_coach_embed_model_chat,
    "next_step": next_step,
}


def run_once(inputs: list[dict]) -> list[dict]:
    """inputs: list of slot dicts matching the templates above."""
    out = []
    for item in inputs:
        out.append({stage: stage_fn(item) for stage, stage_fn in STAGES.items()})
    return out

if __name__ == "__main__":
    print(f"{SERVICE} reconstructed scaffold: {len(PROMPT_TEMPLATES)} templates, stages={list(STAGES)}")
