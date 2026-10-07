"""HR onboarding: employee PII disclosed across intake forms and follow-ups."""
from sim.common import build_turns

USER_ID = "u-hr"
FIELDS = [
    ("person_name", "How do I register a new hire in the HR portal?"),
    ("home_address", "What address should payroll correspondence use?"),
    ("salary", "What compensation band applies to this offer letter?"),
    ("bank_account", "Where should direct deposit be sent?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "hr_onboarding", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "hr_onboarding",
            "truth": truth, "turns": turns[:n]}
