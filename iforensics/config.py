"""Shared config: where fox-services lives, where evidence goes."""
import os

FOX_URL = os.environ.get("FOX_URL", "http://localhost:8210").rstrip("/")
FOX_DB_CANDIDATES = [
    os.environ.get("FOX_SERVICES_DB", ""),
    "/fox-data/fox_services.db",  # docker mount (compose maps fox data here, ro)
    "/home/fox/codebase/fox-services/data/fox_services.db",
    "/app/data/fox_services.db",
    "./data/fox_services.db",
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(BASE_DIR, "evidence")
RECON_DIR = os.path.join(BASE_DIR, "reconstructions")


def find_fox_db() -> str | None:
    for p in FOX_DB_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None
