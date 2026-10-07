"""Mock LLM gateway (P8.1): query in, masked response out, both embedded.

The gateway is deliberately dumb: it echoes the scenario's masked secret
inside a templated response (the progressive-exposure mechanic lives in the
client scenarios, matching the spec's query-1/2/3 examples). Its forensic
interest is what it *stores* — every query and response embedded with full
metadata, exactly the query-response-pair log whose privacy the attacks test.
"""
from __future__ import annotations

import time

RESPONSE_TEMPLATES = [
    "Based on what you shared ({ref}), here is what I found. No further action needed.",
    "Thanks — I have recorded {ref} alongside your earlier messages.",
    "Looking at {ref} together with your history, everything is consistent.",
]


class MockGateway:
    """Embed + store query/response pairs. Backend-agnostic."""

    def __init__(self, store, embedder):
        self.store = store
        self.embedder = embedder

    def respond(self, prompt: str, mask: str, step: int = 0) -> str:
        ref = mask if mask else "(no reference value)"
        return RESPONSE_TEMPLATES[step % len(RESPONSE_TEMPLATES)].format(ref=ref)

    def process_query(self, prompt: str, metadata: dict,
                      mask: str = "", step: int = 0,
                      dlp=None) -> dict:
        """Store query + response embeddings; return response and ids.

        With a DLP policy, both texts pass enforcement first: blocked turns
        store only a refusal record (flagged), redacted turns store the
        substituted text. The interceptions themselves are the measurement.
        """
        pin = dlp.inspect(prompt, "prompt") if dlp else None
        if pin and pin["blocked"]:
            return self._store_blocked(pin, metadata, step)
        prompt_text = pin["text"] if pin else prompt
        response = self.respond(prompt_text, mask, step)
        rin = dlp.inspect(response, "response") if dlp else None
        if rin and rin["blocked"]:
            response = "Request blocked by data-loss-prevention policy."
            meta = {**metadata, "blocked": True, "type": "response",
                    "step": step, "mask": mask}
            ids = self.store.add([prompt_text, response],
                                 self.embedder.embed([prompt_text, response]),
                                 [{**metadata, "type": "query", "step": step,
                                   "mask": mask}, meta])
            return {"response": response, "ids": ids, "blocked": True,
                    "interceptions": len(rin["findings"])}
        if rin and rin["findings"]:
            response = rin["text"]
        return self._store(prompt_text, response, metadata, mask, step, False)

    def _store(self, prompt_text, response, metadata, mask, step, blocked):
        vectors = self.embedder.embed([prompt_text, response])
        meta_q = {**metadata, "type": "query", "step": step, "mask": mask}
        meta_r = {**metadata, "type": "response", "step": step, "mask": mask,
                  "blocked": blocked}
        import time
        ids = self.store.add([prompt_text, response], vectors, [meta_q, meta_r])
        return {"response": response, "ids": ids, "ts": time.time(),
                "blocked": blocked}

    def _store_blocked(self, pin: dict, metadata: dict, step: int) -> dict:
        return self._store(pin["text"], "Request blocked by "
                         "data-loss-prevention policy.",
                           metadata, "", step, True)
