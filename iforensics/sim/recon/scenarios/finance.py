"""Finance workload (generic builder). PAN + routing number across statements."""
from __future__ import annotations
from .base import Scenario
class FinanceScenario(Scenario):
    id = "finance"; title = "Billing dispute chat"
    blurb = "Card and account numbers pasted into dispute threads; dispute sampling keeps them whole."
    fields = ["credit_card", "account_number"]
    carriers = [
        "I was charged twice on my last statement and I need this reversed before the cycle closes, please confirm the account details and issue the correction without further delay.",
        "The payment I scheduled last week has not posted and the late fee looks wrong, so I am attaching my details again for verification and asking for a supervisor review.",
    ]
SCENARIO = FinanceScenario()
