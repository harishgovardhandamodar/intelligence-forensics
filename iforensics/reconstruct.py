"""Builder: reconstruct a runnable scaffold of each observed service's codebase.

We do NOT recover their exact source — we reconstruct the *observable*
codebase: the prompt templates, pipeline stages, I/O schemas and call
patterns proven by the logs, as a working starter project per service.
"""
import json
import os
import re
from . import config

_SCAFFOLD_PY = '''"""{service} — RECONSTRUCTED from fox-services LLM telemetry.
Source: intelligence-forensics evidence ({n_requests} requests, {models}).
This scaffold reproduces the OBSERVED behavior: prompt templates, pipeline
stages and model calls. Fill in sinks marked TODO with the real destination
(DB/graph/dashboard) to get a functional clone.
"""
import os
import urllib.request
import json

FOX_URL = os.environ.get("FOX_URL", "http://localhost:8210")
SERVICE = "{service}"
MODEL = "{primary_model}"

PROMPT_TEMPLATES = {templates_repr}

def call_llm(prompt: str, model: str = MODEL) -> dict:
    body = json.dumps({{"model": model, "messages": [{{"role": "user", "content": prompt}}], "stream": False}}).encode()
    req = urllib.request.Request(
        FOX_URL + "/api/chat", data=body,
        headers={{"Content-Type": "application/json", "X-Service-Name": SERVICE}},
        method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())

{stage_functions}

def run_once(inputs: list[dict]) -> list[dict]:
    """inputs: list of slot dicts matching the templates above."""
    out = []
    for item in inputs:
        out.append({{stage: stage_fn(item) for stage, stage_fn in STAGES.items()}})
    return out

if __name__ == "__main__":
    print(f"{{SERVICE}} reconstructed scaffold: {{len(PROMPT_TEMPLATES)}} templates, stages={{list(STAGES)}}")
'''


def _fn_name(stage: str) -> str:
    name = re.sub(r"[^0-9a-zA-Z_]", "_", stage).strip("_")
    name = re.sub(r"_+", "_", name) or "stage"
    if name[0].isdigit():
        name = "stage_" + name
    return name[:60]


def _stage_fn(stage: str, service: str) -> str:
    fn = _fn_name(stage)
    return (
        f"def {fn}(item: dict) -> dict:\n"
        f'    """Stage `{stage}` — slot-fill first template with item keys."""\n'
        f"    tpl = next(iter(PROMPT_TEMPLATES.values()), '{{item}}')\n"
        f"    try:\n"
        f"        prompt = tpl.format(**item)\n"
        f"    except KeyError:\n"
        f"        prompt = tpl + '\\n\\nINPUT: ' + json.dumps(item)[:2000]\n"
        f"    # TODO: wire sink (graph DB / dashboard / file) here\n"
        f"    return call_llm(prompt)\n"
    )


def build_service(service: str, profile: dict, out_root: str | None = None) -> str:
    out_root = out_root or config.RECON_DIR
    dest = os.path.join(out_root, service)
    os.makedirs(os.path.join(dest, "prompts"), exist_ok=True)
    templates = {}
    for i, t in enumerate(profile.get("fingerprint", {}).get("templates", [])):
        name = f"template_{i + 1}"
        templates[name] = t.get("template", "")[:2000]
        with open(os.path.join(dest, "prompts", f"{name}.txt"), "w") as f:
            f.write(t.get("template", ""))
            f.write("\n\n--- EXAMPLE HEAD ---\n")
            f.write(t.get("example_head", ""))
    models = profile.get("models", {})
    primary = max(models, key=models.get) if models else "qwen3.8:latest"
    stages = profile.get("pipeline", ["capture_prompt", "llm_call"])
    stage_fns = "\n\n".join(_stage_fn(s, service) for s in stages)
    stage_map = "STAGES = {\n" + "\n".join(f'    "{s}": {_fn_name(s)},' for s in stages) + "\n}\n"
    code = _SCAFFOLD_PY.format(
        service=service,
        n_requests=profile.get("requests", 0),
        models=json.dumps(models),
        primary_model=primary,
        templates_repr=json.dumps(templates, indent=2),
        stage_functions=stage_fns + "\n\n" + stage_map,
    )
    with open(os.path.join(dest, "inferred_pipeline.py"), "w") as f:
        f.write(code)
    recon = {
        "service": service,
        "reconstructed_from": {"requests": profile.get("requests"), "models": models,
                                "query_types": profile.get("query_types")},
        "inferred_project": profile.get("project"),
        "pipeline_summary": profile.get("pipeline_summary"),
        "pipeline_stages": stages,
        "io_schema": {"inputs": profile.get("schema_hints"), "prompt_slots": list(templates)},
        "instructions_recovered": profile.get("instructions"),
        "caveats": ["Prompts in fox DB are truncated to ~500-2000 chars and PII-masked; "
                    "templates are heads, not full sources.",
                    "Completion text is NOT logged — outputs must be re-derived by re-running."],
    }
    with open(os.path.join(dest, "RECONSTRUCTED.json"), "w") as f:
        json.dump(recon, f, indent=1)
    readme = (
        f"# {service} — reconstructed\n\n"
        f"Inferred build: **{profile.get('project')}**\n\n"
        f"{profile.get('pipeline_summary')}\n\n"
        f"- Requests observed: {profile.get('requests')}, tokens: {profile.get('total_tokens')}\n"
        f"- Models: {models}\n- Query types: {profile.get('query_types')}\n"
        f"- Pipeline: {' -> '.join(stages)}\n\n"
        f"## Files\n- `inferred_pipeline.py` — runnable scaffold (fill TODO sinks)\n"
        f"- `prompts/template_N.txt` — recovered prompt templates\n"
        f"- `RECONSTRUCTED.json` — machine-readable reconstruction\n"
    )
    with open(os.path.join(dest, "README_RECONSTRUCTED.md"), "w") as f:
        f.write(readme)
    return dest


def build_all(investigation: dict, only: list[str] | None = None) -> list[str]:
    made = []
    for svc, prof in investigation.get("services", {}).items():
        if only and svc not in only:
            continue
        made.append(build_service(svc, prof))
    return made
