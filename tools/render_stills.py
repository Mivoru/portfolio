"""Render every artboard in concept/social.html to PNG with headless Chromium.

Usage: python tools/render_stills.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "concept"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2400, "height": 1600})
    page.goto((ROOT / "concept" / "social.html").as_uri())
    page.evaluate("document.fonts.ready")
    for el in page.query_selector_all(".ab, .bn"):
        name = el.get_attribute("id")
        el.screenshot(path=str(OUT / f"{name}.png"))
        print(name)
    browser.close()
