"""Framework API surface: route catalogue + stdlib transport (see routes)."""
from __future__ import annotations

from .routes import ROUTES, call

__all__ = ["ROUTES", "call"]
