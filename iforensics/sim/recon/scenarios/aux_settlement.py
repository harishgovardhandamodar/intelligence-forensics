"""Inter-bank settlement files (engine-backed). Peer-bank aux lines + masked PAN."""
from __future__ import annotations
from .base import Scenario
class AuxSettlementScenario(Scenario):
    id = "aux_settlement"; title = "Peer-bank settlement files"
    blurb = "Bank B reconstructs Bank A customer PANs from settlement lines it legitimately receives."
    fields = ["credit_card", "account_number"]
    engine_id = "stateless_aux_settlement"
SCENARIO = AuxSettlementScenario()
