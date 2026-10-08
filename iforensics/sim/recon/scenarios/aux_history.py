"""Settled-history bootstrap (engine-backed). Archive first, live session after."""
from __future__ import annotations
from .base import Scenario
class AuxHistoryScenario(Scenario):
    id = "aux_history"; title = "Settled-history bootstrap"
    blurb = "Full past settlements on the same card precede the masked live session."
    fields = ["credit_card"]
    engine_id = "stateless_aux_history"
SCENARIO = AuxHistoryScenario()
