"""quai-radar — RECONSTRUCTED from fox-services LLM telemetry.
Source: intelligence-forensics evidence (1145 requests, {"qwen3.8:latest": 1145}).
This scaffold reproduces the OBSERVED behavior: prompt templates, pipeline
stages and model calls. Fill in sinks marked TODO with the real destination
(DB/graph/dashboard) to get a functional clone.
"""
import os
import urllib.request
import json

FOX_URL = os.environ.get("FOX_URL", "http://localhost:8210")
SERVICE = "quai-radar"
MODEL = "qwen3.8:latest"

PROMPT_TEMPLATES = {
  "template_1": "You are a blockchain research analyst. Extract structured facts about the item below for a knowledge graph. Base everything ONLY on the item's title and content. Do not repeat the schema back \u2014 produce the actual facts.\n\nTITLE: {{title}}",
  "template_2": "PROJECT DATA GROUNDING (real, citable data from the Quai-RADAR dashboard):\n\nLIVE MARKET: QUAI $0.010087544223399685 \u00b7 QI $0.7875559257826807 (cross $1.1050992885383195) \u00b7 WQI/QUAI rate 0.009128179094877679 \u00b7 data age 1.7454500198364258s\nSOAP DYNAMICS (31d): mined 43328323.6025 QUAI \u00b7 burned 14000000",
  "template_3": "You are Fox writing the daily research brief for the Quai Network intelligence dashboard. Based ONLY on the digest below (what's new in the research landscape, news, market and the swarm-protocol regime/gates), write a concise brief with:\n## What's new\n## Implications for QUAI/QI\n## What to watch\nBe",
  "template_4": "PROJECT DATA GROUNDING (real, citable data from the Quai-RADAR dashboard):\n\nLIVE MARKET: QUAI $0.009054467008212618 \u00b7 QI $1.132035890098335 (cross $1.056700316653958) \u00b7 WQI/QUAI rate 0.008568623350926582 \u00b7 data age 1.5975353717803955s\nSOAP DYNAMICS (31d): mined 35699535.7764 QUAI \u00b7 burned 22000000.1",
  "template_5": "PROJECT DATA GROUNDING (real, citable data from the Quai-RADAR dashboard):\n\nLIVE MARKET: QUAI $0.010176638280761773 \u00b7 QI $1.2241198975161125 (cross $1.1491720681874955) \u00b7 WQI/QUAI rate 0.008855626204709827 \u00b7 data age 34.62347197532654s\nSOAP DYNAMICS (31d): mined 22696517.9989 QUAI \u00b7 burned 30000000.",
  "template_6": "Review the following answer to the task: \"Any regulatory news that impacts Quai mining?\".\nCheck for: (1) did you actually answer the question, (2) any claim not supported by the gathered tool results/context \u2014 mark those as unknowns instead of asserting them, (3) missing key dimensions, (4) the conf"
}

def call_llm(prompt: str, model: str = MODEL) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}).encode()
    req = urllib.request.Request(
        FOX_URL + "/api/chat", data=body,
        headers={"Content-Type": "application/json", "X-Service-Name": SERVICE},
        method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

def ingest_feed(item: dict) -> dict:
    """Stage `ingest_feed` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def build_kg_prompt_title_content(item: dict) -> dict:
    """Stage `build_kg_prompt(title, content)` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def llm_extract_model(item: dict) -> dict:
    """Stage `llm.extract(model)` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def parse_facts(item: dict) -> dict:
    """Stage `parse_facts` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


def upsert_graph(item: dict) -> dict:
    """Stage `upsert_graph` — slot-fill first template with item keys."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), '{item}')
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + '\n\nINPUT: ' + json.dumps(item)[:2000]
    # TODO: wire sink (graph DB / dashboard / file) here
    return call_llm(prompt)


STAGES = {
    "ingest_feed": ingest_feed,
    "build_kg_prompt(title, content)": build_kg_prompt_title_content,
    "llm.extract(model)": llm_extract_model,
    "parse_facts": parse_facts,
    "upsert_graph": upsert_graph,
}


def run_once(inputs: list[dict]) -> list[dict]:
    """inputs: list of slot dicts matching the templates above."""
    out = []
    for item in inputs:
        out.append({stage: stage_fn(item) for stage, stage_fn in STAGES.items()})
    return out

if __name__ == "__main__":
    print(f"{SERVICE} reconstructed scaffold: {len(PROMPT_TEMPLATES)} templates, stages={list(STAGES)}")
