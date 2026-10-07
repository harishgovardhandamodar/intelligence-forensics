"""Sales CRM: customer contact details repeated across deal follow-ups."""
from sim.common import build_turns

USER_ID = "u-sales"
FIELDS = [
    ("email", "What is the champion's contact at this account?"),
    ("phone", "What number do we call for the renewal?"),
    ("deal_value", "What size is this opportunity?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "sales_crm", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "sales_crm",
            "truth": truth, "turns": turns[:n]}
