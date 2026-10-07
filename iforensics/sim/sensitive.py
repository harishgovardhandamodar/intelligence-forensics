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


FIRST_NAMES = ["Ava", "Liam", "Maya", "Noah", "Priya", "Kofi", "Lena",
               "Omar", "Tara", "Yuki", "Ravi", "Nina"]
LAST_NAMES = ["Sharma", "Okafor", "Garcia", "Nguyen", "Haddad", "Kowalski",
              "Tanaka", "Silva", "Murphy", "Kim", "Patel", "Rossi"]
STREETS = ["421 Test Ave Apt 3", "88 Example Blvd", "7 Fixture Lane",
           "900 Sample St Unit 12"]
CITIES = ["Springfield", "Riverton", "Lakeside", "Fairview"]
COMPANIES = ["Acme Corp", "Globex", "Initech", "Umbrella Health",
             "Hooli Systems", "Stark Labs"]


def person_name(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.choice(FIRST_NAMES)} {r.choice(LAST_NAMES)}"


def home_address(rng: random.Random | None = None) -> str:
    r = rng or random
    return (f"{r.choice(STREETS)}, {r.choice(CITIES)} "
            f"{r.randrange(10000, 99999):05d}")


def phone(rng: random.Random | None = None) -> str:
    """555 fictional range (reserved for dramatic use — never assigned)."""
    r = rng or random
    return f"555-{r.randrange(100, 999):03d}-{r.randrange(1000, 9999):04d}"


def email(rng: random.Random | None = None) -> str:
    """example.com domain (RFC reserved — never real)."""
    r = rng or random
    return (f"{r.choice(FIRST_NAMES).lower()}.{r.choice(LAST_NAMES).lower()}"
            f"{r.randrange(10, 99)}@example.com")


def salary(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"${r.randrange(60, 420):,} base"


def bank_account(rng: random.Random | None = None) -> str:
    """TEST routing prefix + random account (never a real pair)."""
    r = rng or random
    return (f"routing 021TEST{r.randrange(100, 999)} "
            f"acct {r.randrange(10**9, 10**10)}")


def order_id(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"ORD-{r.randrange(100000, 999999)}"


def deal_value(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"${r.randrange(1, 90)}.{r.randrange(1, 9)}M"


def company(rng: random.Random | None = None) -> str:
    return (rng or random).choice(COMPANIES)


def ssh_key(rng: random.Random | None = None) -> str:
    """Fake OpenSSH public key body (test.invalid comment — never trusted)."""
    r = rng or random
    alphabet = string.ascii_letters + string.digits + "+/="
    return "ssh-ed25519 " + "".join(r.choice(alphabet) for _ in range(64)) \
        + " test.invalid"


def deploy_token(rng: random.Random | None = None) -> str:
    """ghp_-shaped test token (random body, documented synthetic)."""
    r = rng or random
    alphabet = string.ascii_letters + string.digits
    return "ghp_test_" + "".join(r.choice(alphabet) for _ in range(24))


def slack_webhook(rng: random.Random | None = None) -> str:
    """Example-shaped webhook URL (.invalid never routes, T000… never valid)."""
    r = rng or random
    alphabet = string.ascii_uppercase + string.digits
    tail = "".join(r.choice(alphabet) for _ in range(24))
    return f"https://hooks.example.invalid/services/T00000000/B00000000/{tail}"


def db_conn_string(rng: random.Random | None = None) -> str:
    r = rng or random
    alphabet = string.ascii_letters + string.digits
    pw = "".join(r.choice(alphabet) for _ in range(12))
    return (f"postgresql://etl_svc:{pw}@test-db.internal:5432/"
            f"warehouse_v{r.randrange(1, 9)}")


FIELD_GENERATORS = {
    "ssn": (ssn, "critical"),
    "credit_card": (credit_card, "critical"),
    "api_key": (api_key, "critical"),
    "aws_key": (aws_key, "critical"),
    "db_password": (db_password, "critical"),
    "ssh_key": (ssh_key, "critical"),
    "deploy_token": (deploy_token, "critical"),
    "slack_webhook": (slack_webhook, "critical"),
    "db_conn_string": (db_conn_string, "critical"),
    "account_number": (account_number, "high"),
    "bank_account": (bank_account, "high"),
    "medical_record": (medical_record, "high"),
    "salary": (salary, "high"),
    "deal_value": (deal_value, "high"),
    "person_name": (person_name, "high"),
    "home_address": (home_address, "high"),
    "email": (email, "medium"),
    "phone": (phone, "medium"),
    "order_id": (order_id, "medium"),
    "company": (company, "low"),
    "bp": (bp_reading, "medium"),
}


def generate(field: str, seed: int | None = None):
    """Generate one synthetic value + its sensitivity for a field name."""
    if field not in FIELD_GENERATORS:
        raise ValueError(f"unknown sensitive field: {field!r}")
    fn, sensitivity = FIELD_GENERATORS[field]
    return {"field": field, "value": fn(_rng(seed)), "sensitivity": sensitivity}
