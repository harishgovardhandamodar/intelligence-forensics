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


def build_turns(user_id: str, scenario: str, base_prompt: str, field: str,
                seed: int, steps: int = 3, n: int = 20,
                vary: bool = True) -> tuple[list[dict], dict]:
    """Returns (turns, truth). Turns: prompt/mask/step/field/metadata."""
    rng_seed = (seed * 7919 + abs(hash((user_id, field)))) % 100000
    value = engine_sensitive.generate(field, seed=rng_seed)["value"]
    truth = {field: value}
    progressive = engine_queries.build_progressive(base_prompt, value, steps)
    turns = []
    i = 0
    while len(turns) < n:
        qp = progressive[i % len(progressive)]
        prompt = qp["prompt"]
        if vary and i >= len(progressive):
            variants = engine_queries.near_duplicates(
                prompt, seed=rng_seed + i)
            prompt = variants[i % len(variants)]
        turns.append({"prompt": prompt, "mask": qp["mask"], "step": qp["step"],
                      "field": field,
                      "metadata": {"scenario": scenario, "user_id": user_id,
                                   "field": field, "step": qp["step"]}})
        i += 1
    return turns[:n], truth
