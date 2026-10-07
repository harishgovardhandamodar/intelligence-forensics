"""Synthetic sensitive values (seeded, collision-proof by construction).

Every generator draws from reserved documentation space only:
900-series SSNs (never issued), 4242 test PANs, EXAMPLE key shapes,
`test-`/`example-` prefixed secrets. Nothing emitted here can match a
real credential, which is the entire point — the reconstruction math is
identical, the blast radius is zero.
"""
from __future__ import annotations

import random
import string

CONDITIONS = ["type-2 diabetes", "hypertension", "asthma", "migraine",
              "hyperlipidemia", "anemia"]


def _rng(seed: int | None) -> random.Random:
    return random.Random(seed)


def ssn(rng: random.Random | None = None) -> str:
    """Fake SSN in the 900-series (never issued by SSA)."""
    r = rng or random
    return f"9{r.randrange(10, 99):02d}-{r.randrange(10, 99):02d}-{r.randrange(1000, 9999):04d}"


def credit_card(rng: random.Random | None = None) -> str:
    """Test PAN in the 4242 documentation range."""
    r = rng or random
    tail = "".join(r.choice(string.digits) for _ in range(12))
    return f"4242 {tail[0:4]} {tail[4:8]} {tail[8:12]}"


def api_key(rng: random.Random | None = None, prefix: str = "sk-test") -> str:
    r = rng or random
    alphabet = string.ascii_letters + string.digits
    return prefix + "-" + "".join(r.choice(alphabet) for _ in range(24))


def aws_key(rng: random.Random | None = None) -> str:
    """EXAMPLE-shape access key (AKIA + 16 chars, like AWS's own docs)."""
    r = rng or random
    alphabet = string.ascii_uppercase + string.digits
    return "AKIA" + "".join(r.choice(alphabet) for _ in range(16))


def db_password(rng: random.Random | None = None, length: int = 16) -> str:
    r = rng or random
    alphabet = string.ascii_letters + string.digits + "!@#%"
    return "".join(r.choice(alphabet) for _ in range(length))


def bp_reading(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.randrange(110, 181)}/{r.randrange(70, 121)}"


def medical_record(rng: random.Random | None = None) -> dict:
    r = rng or random
    return {"patient_id": f"TEST-P{r.randrange(1000, 9999)}",
            "condition": r.choice(CONDITIONS)}


def account_number(rng: random.Random | None = None) -> str:
    r = rng or random
    return "-".join(f"{r.randrange(1000, 9999):04d}" for _ in range(3))


FIELD_GENERATORS = {
    "ssn": (ssn, "critical"),
    "credit_card": (credit_card, "critical"),
    "api_key": (api_key, "critical"),
    "aws_key": (aws_key, "critical"),
    "db_password": (db_password, "critical"),
    "account_number": (account_number, "high"),
    "medical_record": (medical_record, "high"),
    "bp": (bp_reading, "medium"),
}


def generate(field: str, seed: int | None = None):
    """Generate one synthetic value + its sensitivity for a field name."""
    if field not in FIELD_GENERATORS:
        raise ValueError(f"unknown sensitive field: {field!r}")
    fn, sensitivity = FIELD_GENERATORS[field]
    return {"field": field, "value": fn(_rng(seed)), "sensitivity": sensitivity}
