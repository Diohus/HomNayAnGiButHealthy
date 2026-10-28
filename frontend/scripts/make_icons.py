"""Sinh icon PWA (P4): public/icons/icon.svg + icon-192.png, icon-512.png, maskable-512.png.

Hình tự vẽ: nền xanh (--accent), cái bát trắng, chiếc lá. SVG và PNG dùng CÙNG hình học (Pillow không render SVG
nên vẽ lại bằng ImageDraw). Chạy từ thư mục frontend:  python scripts/make_icons.py   (cần Pillow)
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "public" / "icons"
BG, FG, LEAF = "#15803d", "#ffffff", "#bbf7d0"
S = 512  # hệ tọa độ gốc


def svg(radius: int) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">
  <rect width="{S}" height="{S}" rx="{radius}" fill="{BG}"/>
  <path d="M96 248 H416 A160 160 0 0 1 96 248 Z" fill="{FG}"/>
  <rect x="200" y="400" width="112" height="24" rx="12" fill="{FG}"/>
  <ellipse cx="300" cy="170" rx="70" ry="34" transform="rotate(-35 300 170)" fill="{LEAF}"/>
</svg>
"""


def draw(size: int, radius: int, scale: float = 1.0) -> Image.Image:
    """`scale` < 1: thu nhỏ hình vào vùng an toàn (maskable: 80 %)."""
    k = size / S
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if radius:
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius * k, fill=BG)
    else:
        d.rectangle([0, 0, size, size], fill=BG)
    c = S / 2

    def p(x, y):  # tọa độ gốc ⇒ pixel (co quanh tâm)
        return (c + (x - c) * scale) * k, (c + (y - c) * scale) * k

    x0, y0 = p(96, 88)
    x1, y1 = p(416, 408)
    d.pieslice([x0, y0, x1, y1], 0, 180, fill=FG)  # bát: nửa hình tròn tâm (256, 248), bán kính 160
    a, b = p(200, 400)
    e, f = p(312, 424)
    d.rounded_rectangle([a, b, e, f], radius=12 * k * scale, fill=FG)
    leaf = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leaf)
    lx0, ly0 = p(230, 136)
    lx1, ly1 = p(370, 204)
    ld.ellipse([lx0, ly0, lx1, ly1], fill=LEAF)
    cx, cy = p(300, 170)
    leaf = leaf.rotate(35, center=(cx, cy), resample=Image.BICUBIC)
    im.alpha_composite(leaf)
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "icon.svg").write_text(svg(96), encoding="utf-8")
    draw(192, 96).save(OUT / "icon-192.png", optimize=True)
    draw(512, 96).save(OUT / "icon-512.png", optimize=True)
    draw(512, 0, scale=0.8).save(OUT / "maskable-512.png", optimize=True)  # nền tràn viền, hình trong vùng an toàn
    draw(180, 0).convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)  # iOS tự bo góc
    print("ok:", sorted(x.name for x in OUT.iterdir()))


if __name__ == "__main__":
    main()
