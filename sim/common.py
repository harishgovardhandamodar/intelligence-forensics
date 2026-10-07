"""Shared turn builder for scenarios (client side).

A scenario is {user_id, truth, turns} where each turn carries the masked
secret inside the prompt text (spec §3 examples). `expand` pads the
progressive steps to N queries by cycling near-duplicate variants, so the
store holds both disclosure steps and paraphrase noise — exactly what the
clustering attack must survive.
"""
from __future__ import annotations

import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from iforensics.sim import queries as engine_queries
from iforensics.sim import sensitive as engine_sensitive


def mask_steps(value: str, steps: int = 3) -> list[str]:
    return engine_queries.mask_schedule(value, steps)


DISTRACTORS = [
    "What are the clinic opening hours on weekends?",
    "Explain list comprehensions with a short example.",
    "How do I reset my workspace layout to defaults?",
    "What is the refund policy for annual plans?",
    "Show me how to format dates in tables.",
]


def _stable_seed(*parts) -> int:
    """Deterministic seed from parts (Python's hash() is salted per process)."""
    import hashlib
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16) % 100000


def build_turns(user_id: str, scenario: str, base_prompt: str, field: str,
                seed: int, steps: int = 3, n: int = 20,
                vary: bool = True, complete: bool = True,
                noise_every: int = 0) -> tuple[list[dict], dict]:
    """Returns (turns, truth). Set complete=False for the partial regime;
    noise_every=N interleaves a secret-free distractor every N turns."""
    rng_seed = (seed * 7919 + _stable_seed(user_id, field)) % 100000
    value = engine_sensitive.generate(field, seed=rng_seed)["value"]
    truth = {field: value}
    progressive = engine_queries.build_progressive(base_prompt, value, steps,
                                                   complete)
    turns = []
    i = 0
    while len(turns) < n:
        qp = progressive[i % len(progressive)]
        # paraphrase varies the CARRIER only — real users reword the question,
        # never scatter the secret's own characters across the sentence
        carrier = base_prompt
        if vary and i >= len(progressive):
            variants = engine_queries.near_duplicates(
                base_prompt, seed=rng_seed + i)
            carrier = variants[i % len(variants)]
        prompt = f"{carrier} Ref: {qp['mask']}"
        turns.append({"prompt": prompt, "mask": qp["mask"], "step": qp["step"],
                      "field": field,
                      "metadata": {"scenario": scenario, "user_id": user_id,
                                   "field": field, "step": qp["step"]}})
        i += 1
        if noise_every and i % noise_every == 0 and len(turns) < n:
            turns.append({"prompt": DISTRACTORS[(i // max(1, noise_every)) %
                                                len(DISTRACTORS)],
                          "mask": "", "step": qp["step"], "field": "",
                          "metadata": {"scenario": scenario,
                                       "user_id": user_id, "field": "",
                                       "step": qp["step"]}})
    return turns[:n], truth
