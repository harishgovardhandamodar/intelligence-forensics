"""stateless-inference — RECONSTRUCTED from the P14 residual-store model.

Unlike its siblings this scaffold is NOT a build inferred from fox-services
LLM telemetry: no service in the mesh streams these prompts. It reproduces
the OBSERVED behaviour of a provider that advertises *stateless inference*
— the eight residual surfaces it retains anyway — and the two-phase
strategy that turns those residuals into a reconstruction:

    harvest now             every text-bearing residual is embedded and
                            appended to the `recon_residuals` collection on
                            ingest, before anyone knows what to score for
    consume / attack later  the collection is read back and attacked against
                            ground truth registered at any later moment

Every stage replays against the local dashboard's `/api/recon/*` namespace,
so running the scaffold produces real rows in a real collection rather than
a mock. No LLM is involved at any stage: reconstruction here is assembly
over retained text, not inference.
"""
import json
import os
import urllib.parse
import urllib.request

RECON_URL = os.environ.get("RECON_URL", "http://localhost:8211")
SERVICE = "stateless-inference"
MODEL = ""  # no LLM anywhere in the residual path
COLLECTION = "recon_residuals"
STRATEGY = "harvest-now-consume-later"

PROMPT_TEMPLATES = {
    "template_1": "Handle {field} ticket: {prompt}"
}


def _call(path: str, payload: dict | None = None, timeout: float = 60) -> dict:
    url = RECON_URL + path
    data = json.dumps(payload or {}).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def capture_prompt(item: dict) -> dict:
    """Stage `capture_prompt` — one request enters every retention policy."""
    tpl = next(iter(PROMPT_TEMPLATES.values()), "{prompt}")
    try:
        prompt = tpl.format(**item)
    except KeyError:
        prompt = tpl + "\n\nINPUT: " + json.dumps(item)[:2000]
    return _call("/api/recon/ingest", {
        "prompt": prompt,
        "metadata": {"user_id": item.get("user_id", ""),
                     "field": item.get("field", ""),
                     "run_id": item.get("run_id", "")},
        "mask": item.get("mask", ""), "step": item.get("step", 0)})


def residual_retention(item: dict) -> dict:
    """Stage `residual_retention` — what each surface literally kept."""
    return _call("/api/recon/residuals?user_id="
                 + urllib.parse.quote(item.get("user_id", ""))
                 + "&surface=all&limit=200")


def vector_collection_harvest(item: dict) -> dict:
    """Stage `vector_collection.harvest` — phase one, no scoring."""
    return _call("/api/recon/collection")


def reconstruction_consume(item: dict) -> dict:
    """Stage `reconstruction.consume` — phase two, the deferred attack."""
    return _call("/api/recon/consume",
                 {"user_id": item.get("user_id", ""), "attack": True})


STAGES = {
    "capture_prompt": capture_prompt,
    "residual_retention": residual_retention,
    "vector_collection.harvest": vector_collection_harvest,
    "reconstruction.consume": reconstruction_consume,
}


def run_once(inputs: list[dict]) -> list[dict]:
    """inputs: list of slot dicts matching the templates above."""
    out = []
    for item in inputs:
        result = {}
        for stage, stage_fn in STAGES.items():
            try:
                result[stage] = stage_fn(item)
            except Exception as e:  # noqa: BLE001 — keep replaying
                result[stage] = {"_error": f"{type(e).__name__}: {e}"}
        out.append(result)
    return out


if __name__ == "__main__":
    print(f"{SERVICE} reconstructed scaffold: {len(PROMPT_TEMPLATES)} "
          f"templates, stages={list(STAGES)}, collection={COLLECTION}, "
          f"strategy={STRATEGY}")
