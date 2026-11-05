"""Render assets/icon.png, icon-1024.png and icon.ico (run once; output is committed).

The icon: a rounded blue-to-teal tile with a white "hub" — one centre node linked to three devices.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024
K = 2  # draw at 2x, then downsample for smooth edges


def gradient(size, c1, c2):
    base = Image.new("RGB", (size, size), c1)
    top = Image.new("RGB", (size, size), c2)
    v = Image.linear_gradient("L").resize((size, size))
    mask = Image.blend(v, v.rotate(90), 0.5)
    return Image.composite(top, base, mask)


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg = gradient(S, (37, 99, 235), (14, 165, 164)).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([40, 40, S - 40, S - 40], radius=230, fill=255)
    img.paste(bg, (0, 0), mask)

    big = Image.new("RGBA", (S * K, S * K), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    cx, cy = 512 * K, 540 * K
    nodes = []
    for ang in (-90, 30, 150):
        a = math.radians(ang)
        nodes.append((cx + math.cos(a) * 300 * K, cy + math.sin(a) * 300 * K))
    # soft rings (wireless)
    for r, alpha in ((250, 50), (360, 30)):
        d.ellipse([cx - r * K, cy - r * K, cx + r * K, cy + r * K], outline=(255, 255, 255, alpha), width=16 * K)
    for x, y in nodes:
        d.line([(cx, cy), (x, y)], fill=(255, 255, 255, 255), width=34 * K)
    for x, y in nodes:
        r = 92 * K
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255))
        r2 = 58 * K
        d.ellipse([x - r2, y - r2, x + r2, y + r2], fill=(219, 234, 254, 255))
    # centre node with share arrow
    r = 150 * K
    shadow = Image.new("RGBA", (S * K, S * K), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([cx - r + 10 * K, cy - r + 24 * K, cx + r + 10 * K, cy + r + 24 * K],
                                   fill=(10, 30, 80, 110))
    big = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(20 * K)), big)
    d = ImageDraw.Draw(big)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
    r2 = 122 * K
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(249, 115, 22, 255))
    # up arrow
    w = 26 * K
    d.line([(cx, cy + 62 * K), (cx, cy - 50 * K)], fill=(255, 255, 255, 255), width=w)
    d.polygon([(cx, cy - 86 * K), (cx - 58 * K, cy - 24 * K), (cx + 58 * K, cy - 24 * K)], fill=(255, 255, 255, 255))
    img = Image.alpha_composite(img, big.resize((S, S), Image.LANCZOS))

    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(ROOT, "assets", "icon.png"))
    img.save(os.path.join(ROOT, "assets", "icon-1024.png"))
    img.save(os.path.join(ROOT, "assets", "icon.ico"),
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
