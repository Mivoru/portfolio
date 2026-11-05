"""Render the display ads and the slide in concept/ads.html to PNG and WebP.

Ads render at 2x for sharp text on high-density screens.

Usage: python tools/render_ads.py
"""
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "concept"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2400, "height": 1600}, device_scale_factor=2)
    page.goto((ROOT / "concept" / "ads.html").as_uri())
    page.evaluate("document.fonts.ready")
    for element in page.query_selector_all(".ad, .slide"):
        name = element.get_attribute("id")
        target = OUT / f"{name}.png"
        element.screenshot(path=str(target))
        image = Image.open(target).convert("RGB")
        if name == "s1":
            image = image.resize((1920, 1080), Image.LANCZOS)
            image.save(target)
        image.save(target.with_suffix(".webp"), quality=88)
        print(name, image.size)
    browser.close()
