"""Legal contracts (generic builder). Names + deal values under review."""
from __future__ import annotations
from .base import Scenario
class LegalContractsScenario(Scenario):
    id = "legal_contracts"; title = "Contract review assistant"
    blurb = "Counterparty names and deal values circulate through redline threads; snapshots keep them."
    fields = ["deal_value", "company", "person_name"]
    engine_id = "stateless_legal"
    carriers = [
        "Please review the attached clause on payment terms and confirm the counterparty details match the term sheet before we circulate the next redline to counsel.",
        "The renewal carries a different value than last year and I need a plain-language summary of what changed, who approved it, and which exhibits reference it.",
    ]
SCENARIO = LegalContractsScenario()
