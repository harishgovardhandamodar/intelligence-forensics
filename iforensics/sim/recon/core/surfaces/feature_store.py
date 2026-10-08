"""Feature store incl. raw text (staged). 1/40 whole — 400-day window."""
from __future__ import annotations
from .staged import StagedSurface
class FeatureStoreSurface(StagedSurface):
    id = "feature_store"; title = "Feature store"
    rate_num = 1; rate_den = 40; head_chars = 0
SURFACE = FeatureStoreSurface()
