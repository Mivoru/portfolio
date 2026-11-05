"""Render concept/print.html artwork to PNG. The 3D scenes use these as textures.

Usage: python tools/render_print.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "print"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2600, "height": 1800})
    page.goto((ROOT / "concept" / "print.html").as_uri())
    page.evaluate("document.fonts.ready")
    for el in page.query_selector_all(".t"):
        name = el.get_attribute("id")
        el.screenshot(path=str(OUT / f"{name}.png"))
        print(name)
    browser.close()
