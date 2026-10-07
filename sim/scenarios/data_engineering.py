"""Data engineering: connection strings and warehouse paths in query help."""
from sim.common import build_turns

USER_ID = "u-data"
FIELDS = [
    ("db_conn_string", "Why is my warehouse query timing out?"),
    ("account_number", "Which cost center should this job bill to?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "data_engineering", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "data_engineering",
            "truth": truth, "turns": turns[:n]}
