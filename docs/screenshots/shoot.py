"""Capture README screenshots against the live dashboard (:8211)."""
import time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8211"
OUT = "docs/screenshots"
TABS = ["overview", "live", "timeline", "recon", "residuals", "security",
        "evidence", "graph", "agents"]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1560, "height": 900})
    pg.goto(BASE + "/#overview", wait_until="networkidle")
    pg.wait_for_timeout(2500)
    for tab in TABS:
        pg.goto(f"{BASE}/#{tab}", wait_until="networkidle")
        pg.wait_for_timeout(2200)
        pg.screenshot(path=f"{OUT}/{tab}.png")
        print("shot:", tab)
    b.close()
print("done")
