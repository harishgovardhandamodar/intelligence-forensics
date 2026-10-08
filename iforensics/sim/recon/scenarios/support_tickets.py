"""Support tickets → engine stateless_support (exact behavior)."""
from __future__ import annotations
from .base import Scenario
class SupportTicketsScenario(Scenario):
    id = "support_tickets"; title = "Support ticket triage"
    blurb = "Customers paste credentials into tickets; support views and snapshots retain them."
    fields = ["email", "phone"]; engine_id = "stateless_support"
SCENARIO = SupportTicketsScenario()
