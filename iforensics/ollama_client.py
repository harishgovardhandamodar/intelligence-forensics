"""Ollama client for local inference (stdlib only — no extra deps).

Default model: qwen3.8:27b served by local Ollama (:11434).
`think: false` is forced: the Qwen3 hybrid thinker is slow and leaks
reasoning tokens; for forensic agents we want fast direct answers.
"""
import json
import os
import time
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("IF_MODEL", "qwen3.8:27b")
DEFAULT_TIMEOUT = float(os.environ.get("IF_LLM_TIMEOUT_S", "300"))


class OllamaError(RuntimeError):
    pass


def _post(path: str, payload: dict, timeout: float) -> dict:
    url = OLLAMA_URL + path
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        raise OllamaError(f"{url}: {type(e).__name__}: {e}") from e


def chat(messages: list[dict], model: str = MODEL, num_predict: int = 512,
         temperature: float = 0.2, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Non-streaming /api/chat. Returns {content, prompt_tokens, completion_tokens, ms}."""
    t0 = time.time()
    resp = _post("/api/chat", {
        "model": model,
        "think": False,  # fast path, no reasoning spill
        "stream": False,
        "messages": messages,
        "options": {"num_predict": num_predict, "temperature": temperature},
    }, timeout)
    msg = resp.get("message") or {}
    return {
        "content": (msg.get("content") or "").strip(),
        "prompt_tokens": resp.get("prompt_eval_count", 0),
        "completion_tokens": resp.get("eval_count", 0),
        "ms": round((time.time() - t0) * 1000, 1),
        "model": resp.get("model", model),
    }


def ask(system: str, user: str, **kw) -> dict:
    return chat([{"role": "system", "content": system},
                 {"role": "user", "content": user}], **kw)


def ask_json(system: str, user: str, **kw) -> dict:
    """Ask and parse a JSON object from the reply (tolerant: code fences, prose)."""
    out = ask(system, user + "\n\nReply with a single JSON object, no prose.", **kw)
    raw = out["content"]
    body = raw
    if "```" in raw:  # strip code fences
        parts = raw.split("```")
        for p in parts:
            p = p.strip().lstrip("json").strip()
            if p.startswith("{") and p.endswith("}"):
                body = p
                break
    start, end = body.find("{"), body.rfind("}")
    parsed: dict = {}
    if start >= 0 and end > start:
        try:
            parsed = json.loads(body[start:end + 1])
        except json.JSONDecodeError:
            parsed = {}
    out["parsed"] = parsed
    out["raw"] = raw
    return out


def ping(model: str = MODEL) -> dict:
    try:
        r = ask("You are a health check.", "Reply with exactly: OK",
                model=model, num_predict=5, timeout=60)
        return {"ok": r["content"].strip().upper().startswith("OK"),
                "model": model, "ms": r["ms"], "url": OLLAMA_URL}
    except OllamaError as e:
        return {"ok": False, "model": model, "error": str(e), "url": OLLAMA_URL}
