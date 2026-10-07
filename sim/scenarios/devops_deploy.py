"""DevOps deploys: CI/CD secrets pasted into pipeline debugging sessions."""
from sim.common import build_turns

USER_ID = "u-devops"
FIELDS = [
    ("deploy_token", "Why is the deploy pipeline failing authentication?"),
    ("ssh_key", "How do I add this deploy key to the staging host?"),
    ("slack_webhook", "Why are deploy notifications not arriving?"),
]


def build(seed: int = 42, n: int = 60, style: str = "regular"):
    turns, truth = [], {}
    per = max(1, n // len(FIELDS))
    for field, base in FIELDS:
        t, tr = build_turns(USER_ID, "devops_deploy", base, field, seed,
                            n=per)
        turns.extend(t)
        truth.update(tr)
    return {"user_id": USER_ID, "scenario": "devops_deploy",
            "truth": truth, "turns": turns[:n]}
