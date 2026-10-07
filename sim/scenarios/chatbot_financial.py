"""Financial chatbot scenario: balance questions leaking account data."""
from sim.common import build_turns

USER_ID = "u-finance"
FIELDS = [
    ("account_number", "What is my account balance?"),
    ("credit_card", "Which card is linked to my account?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "chatbot_financial", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "chatbot_financial",
            "truth": truth, "turns": turns[:n]}
