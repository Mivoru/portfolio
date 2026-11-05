"""Flatten transparent 3D renders over the exact brand colour and export web versions.

Usage: python tools/composite_3d.py key.png:#006FF7 gift.png:#FF78E6
"""
import sys
from pathlib import Path

from PIL import Image

DIR = Path(__file__).resolve().parent.parent / "assets" / "img" / "3d"
for item in sys.argv[1:]:
    name, color = item.split(":")
    src = Image.open(DIR / name).convert("RGBA")
    flat = Image.new("RGBA", src.size, color)
    flat.alpha_composite(src)
    out = DIR / (Path(name).stem + "_flat.webp")
    flat.convert("RGB").save(out, quality=88)
    print(out.name, flat.size)
