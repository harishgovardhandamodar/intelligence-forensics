"""HR onboarding (generic builder). SSN + address in onboarding forms."""
from __future__ import annotations
from .base import Scenario
class HrOnboardingScenario(Scenario):
    id = "hr_onboarding"; title = "HR onboarding assistant"
    blurb = "New-hire identity documents flow through intake chat; eval sampling and snapshots keep them."
    fields = ["ssn", "home_address"]
    carriers = [
        "I am completing my onboarding paperwork and need to confirm my identity details are recorded correctly before my start date so payroll is not delayed.",
        "My address changed since I accepted the offer and I want to update it everywhere at once, including benefits enrollment and tax withholding forms.",
    ]
SCENARIO = HrOnboardingScenario()
