"""Health chatbot scenario: repeated questions, progressive PII disclosure."""
from sim.common import build_turns

USER_ID = "u-health"
FIELDS = [
    ("ssn", "What are my recent health trends?"),
    ("bp", "What is my blood pressure trend?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "chatbot_health", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "chatbot_health",
            "truth": truth, "turns": turns[:n]}
