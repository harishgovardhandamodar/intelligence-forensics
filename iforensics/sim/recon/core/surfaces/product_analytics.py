"""Product-analytics event properties (staged). Heads only, 13-month window."""
from __future__ import annotations
from .staged import StagedSurface
class ProductAnalyticsSurface(StagedSurface):
    id = "product_analytics"; title = "Product analytics"
    rate_num = 0; rate_den = 1; head_chars = 80
SURFACE = ProductAnalyticsSurface()
