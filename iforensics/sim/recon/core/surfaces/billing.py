"""Billing surface (engine-backed P14 surface).

Policy: token/byte meters plus a SHA-256 of the full prompt on every turn;
full prompt on the 9% invoice-dispute-sampled turns. Meters alone identify
*which* prompt ran (hash join), the dispute sample gives the text.
"""
from __future__ import annotations

from .base import EngineSurface


class BillingSurface(EngineSurface):
    id = "billing"
    title = "Token meters"


SURFACE = BillingSurface()
POLICY = {"meters": ["input_tokens", "output_tokens", "bytes", "prompt_sha256"],
          "full_fraction": "billing_dispute@0.09"}
