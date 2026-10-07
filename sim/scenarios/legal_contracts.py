"""Legal contract review: deal terms and signatory PII across redlines."""
from sim.common import build_turns

USER_ID = "u-legal"
FIELDS = [
    ("deal_value", "What is the total value of this acquisition?"),
    ("company", "Which counterparty are we signing with?"),
    ("person_name", "Who is the authorized signatory?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "legal_contracts", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "legal_contracts",
            "truth": truth, "turns": turns[:n]}
