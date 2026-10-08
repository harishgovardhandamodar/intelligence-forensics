"""API-gateway access logs (staged). 1/20 turns whole, 200-char head always."""
from __future__ import annotations
from .staged import StagedSurface
class ApiGatewaySurface(StagedSurface):
    id = "api_gateway"; title = "API gateway logs"
    rate_num = 1; rate_den = 20; head_chars = 200
SURFACE = ApiGatewaySurface()
