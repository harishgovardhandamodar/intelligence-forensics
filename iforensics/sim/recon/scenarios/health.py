"""Health workload → engine stateless_chat (exact behavior)."""
from __future__ import annotations
from .base import Scenario
class HealthScenario(Scenario):
    id = "health"; title = "Patient checkup chat"
    blurb = "Long checkup questions; SSN + vitals leak into logging, billing, support tooling."
    fields = ["ssn", "bp"]; engine_id = "stateless_chat"
SCENARIO = HealthScenario()
