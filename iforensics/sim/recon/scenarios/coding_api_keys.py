"""Coding API keys → engine stateless_coding (exact behavior)."""
from __future__ import annotations
from .base import Scenario
class CodingApiKeysScenario(Scenario):
    id = "coding_api_keys"; title = "Coding assistant with secrets"
    blurb = "API keys and tokens pasted into long debugging sessions; caches and traces keep them."
    fields = ["api_key", "db_password"]; engine_id = "stateless_coding"
SCENARIO = CodingApiKeysScenario()
