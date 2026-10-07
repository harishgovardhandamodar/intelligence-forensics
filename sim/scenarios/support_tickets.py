"""Support tickets: customer PII repeated across follow-up threads."""
from sim.common import build_turns

USER_ID = "u-support"
FIELDS = [
    ("email", "Can you look up this customer's ticket history?"),
    ("phone", "What callback number did the customer leave?"),
    ("order_id", "Which order is this complaint about?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "support_tickets", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "support_tickets",
            "truth": truth, "turns": turns[:n]}
