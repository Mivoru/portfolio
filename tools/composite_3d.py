"""Flatten transparent 3D renders over the exact brand colour and export web versions.

Every export carries a readable "neoficiální koncept" label in the lower right corner.

Usage: python tools/composite_3d.py key.png:#006FF7 gift.png:#FF78E6
"""
import io
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "assets" / "img" / "3d"
LABEL = "neoficiální koncept · Michal Votýpka"


def render_label(page, size, color):
    """Return the label as a transparent image, set in the concept's mono typeface."""
    page.goto((ROOT / "concept" / "ads.html").as_uri())  # any page that loads brand.css
    page.evaluate(
        """([text, size, color]) => {
          document.body.style.background = 'transparent';
          document.body.innerHTML = `<span id="l" class="spec" style="font-size:${size}px;color:${color}">${text}</span>`;
          return document.fonts.ready.then(() => null);
        }""",
        [LABEL, size, color],
    )
    png = page.locator("#l").screenshot(omit_background=True)
    return Image.open(io.BytesIO(png)).convert("RGBA")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 2000, "height": 300})
    for item in sys.argv[1:]:
        name, color = item.split(":")
        src = Image.open(DIR / name).convert("RGBA")
        flat = Image.new("RGBA", src.size, color)
        flat.alpha_composite(src)
        ink = "#101B2B" if color.upper() == "#FF78E6" else "#FFFFFF"
        label = render_label(page, round(flat.width * 0.016), ink)
        margin = round(flat.width * 0.03)
        flat.alpha_composite(label, (flat.width - label.width - margin, flat.height - label.height - margin))
        out = DIR / (Path(name).stem + "_flat.webp")
        flat.convert("RGB").save(out, quality=88)
        print(out.name, flat.size)
    browser.close()
