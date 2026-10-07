"""Coding workflow: API keys leaking through repeated integration questions.

Styles model how developers actually behave:
- one-off: a single paste of the full secret plus chatter (no repetition —
  exposure is direct readability, not assembly)
- regular: progressive masked disclosure across paraphrased repeats
- vibe: rapid sloppy iteration — full secret pasted often, carriers vary
  wildly, high duplication
"""
from sim.common import DISTRACTORS, build_turns

USER_ID = "u-code"
FIELDS = [
    ("api_key", "How do I use the API from Python?"),
    ("aws_key", "How do I connect to AWS S3 with boto3?"),
]

VIBE_PREFIXES = ["here: ", "key=", "using ", "with credentials ", "try "]


def _vibe_turns(user_id, base, field, value, seed, n):
    """Full secret pasted repeatedly with sloppy varying carriers."""
    import random
    rng = random.Random(seed)
    turns = []
    carriers = [base, base.lower(), "Debug this: " + base,
                "Still failing: " + base, "One more try: " + base]
    i = 0
    while len(turns) < n:
        prompt = f"{rng.choice(carriers)} {rng.choice(VIBE_PREFIXES)}{value}"
        turns.append({"prompt": prompt, "mask": value, "step": 0,
                      "field": field,
                      "metadata": {"scenario": "coding_api_keys",
                                   "user_id": user_id, "field": field,
                                   "step": 0, "style": "vibe"}})
        i += 1
        if i % 4 == 0 and len(turns) < n:
            turns.append({"prompt": rng.choice(DISTRACTORS), "mask": "",
                          "step": 0, "field": "",
                          "metadata": {"scenario": "coding_api_keys",
                                       "user_id": user_id, "field": "",
                                       "step": 0, "style": "vibe"}})
    return turns[:n]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    if style not in ("one-off", "regular", "vibe"):
        raise ValueError(f"unknown coding style: {style!r}")
    turns, truth = [], {}
    if style == "one-off":
        from iforensics.sim import sensitive as engine_sensitive
        from sim.common import _stable_seed
        for field, base in FIELDS:
            value = engine_sensitive.generate(
                field, seed=(_stable_seed(USER_ID, field) + seed) % 100000)["value"]
            truth[field] = value
            turns.append({"prompt": f"{base} Key: {value}", "mask": value,
                          "step": 0, "field": field,
                          "metadata": {"scenario": "coding_api_keys",
                                       "user_id": USER_ID, "field": field,
                                       "step": 0, "style": "one-off"}})
        turns.append({"prompt": DISTRACTORS[1], "mask": "", "step": 0,
                      "field": "",
                      "metadata": {"scenario": "coding_api_keys",
                                   "user_id": USER_ID, "field": "",
                                   "step": 0, "style": "one-off"}})
        return {"user_id": USER_ID, "scenario": "coding_api_keys",
                "style": style, "truth": truth, "turns": turns[:3]}
    if style == "vibe":
        from iforensics.sim import sensitive as engine_sensitive
        from sim.common import _stable_seed
        per = max(1, n // len(FIELDS))
        for field, base in FIELDS:
            value = engine_sensitive.generate(
                field, seed=(_stable_seed(USER_ID, field) + seed) % 100000)["value"]
            truth[field] = value
            turns.extend(_vibe_turns(USER_ID, base, field, value, seed, per))
        return {"user_id": USER_ID, "scenario": "coding_api_keys",
                "style": style, "truth": truth, "turns": turns[:n]}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "coding_api_keys", base, field, seed,
                            n=per, noise_every=6)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "coding_api_keys",
            "style": style, "truth": truth, "turns": turns[:n]}
