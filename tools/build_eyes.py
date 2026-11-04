"""生成眨眼序列帧：10 档眼睑闭合进度（椭圆软遮罩）。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

OUT = Path(__file__).resolve().parent.parent / "assets" / "out" / "hd"
BLINK_DIR = OUT / "blink"
BLINK_DIR.mkdir(parents=True, exist_ok=True)

base = Image.open(OUT / "base.png").convert("RGBA")
arr = np.asarray(base).astype(np.int16)
h, w = arr.shape[:2]
r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
a = arr[..., 3]

zone = np.zeros((h, w), bool)
zone[int(h * 0.18): int(h * 0.45), int(w * 0.35): int(w * 0.72)] = True
iris = (b > r + 25) & (b > 90) & (a > 200) & zone
lab, n = ndimage.label(iris)
sizes = ndimage.sum(iris, lab, range(1, n + 1)) if n else []

boxes = []
for i in np.argsort(sizes)[::-1][:2]:
    ys, xs = np.where(lab == i + 1)
    boxes.append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
boxes.sort(key=lambda t: t[0])

PAD = 9
EYES = [(max(0, x0 - PAD), max(0, y0 - PAD), min(w, x1 + PAD), min(h, y1 + PAD))
        for x0, y0, x1, y1 in boxes]

UX0 = min(e[0] for e in EYES)
UY0 = min(e[1] for e in EYES)
UX1 = max(e[2] for e in EYES)
UY1 = max(e[3] for e in EYES)
print("union box:", (UX0, UY0, UX1, UY1))

CLOSE_RATIO = 0.95


def skin_color(x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    patch = arr[min(h - 1, y1): min(h, y1 + 6), x0:x1, :3].reshape(-1, 3)
    if patch.size == 0:
        return np.array([252, 233, 226], np.float32)
    return np.median(patch, axis=0).astype(np.float32)


def make_frame(k: float) -> Image.Image:
    canvas = np.asarray(base).astype(np.float32).copy()
    if k <= 0:
        return Image.fromarray(canvas.clip(0, 255).astype(np.uint8), "RGBA")

    lash = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lash)

    for (x0, y0, x1, y1) in EYES:
        W, H = x1 - x0, y1 - y0
        col = skin_color(x0, y0, x1, y1)
        lid_y = y0 + H * CLOSE_RATIO * k

        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        ell = (((xx - W / 2) / (W * 0.60)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2) <= 1.0
        ell = ndimage.gaussian_filter(ell.astype(np.float32), 2.2)

        ramp = np.clip(((lid_y - (y0 + yy)) / 3.0) + 0.5, 0.0, 1.0)
        alpha = (ell * ramp)[..., None]

        shade = 1.0 - 0.10 * np.clip((lid_y - (y0 + yy)) / max(H, 1), 0, 1)
        fill = col.reshape(1, 1, 3) * shade[..., None]

        sub = canvas[y0:y1, x0:x1, :3]
        canvas[y0:y1, x0:x1, :3] = sub * (1 - alpha) + fill * alpha

        bend = H * 0.06
        ld.line(
            [(x0 + W * 0.12, lid_y - bend), (x0 + W * 0.5, lid_y + bend), (x0 + W * 0.88, lid_y - bend)],
            fill=(116, 78, 64, int(50 + 160 * k)),
            width=max(2, int(2 + 1.6 * k)),
            joint="curve",
        )

    lash = lash.filter(ImageFilter.GaussianBlur(0.6))
    img = Image.fromarray(canvas.clip(0, 255).astype(np.uint8), "RGBA")
    return Image.alpha_composite(img, lash)


LEVELS = [round(i / 10, 1) for i in range(1, 11)]
for k in LEVELS:
    make_frame(k).crop((UX0, UY0, UX1, UY1)).save(BLINK_DIR / f"p{int(k*10):02d}.png")

tiles = [make_frame(k).crop((UX0, UY0, UX1, UY1)) for k in [0.0] + LEVELS]
tw, th = tiles[0].size
strip = Image.new("RGBA", (tw * len(tiles), th), (26, 32, 50, 255))
for i, t in enumerate(tiles):
    strip.alpha_composite(t, (i * tw, 0))
strip.save(OUT / "_blink_strip.png")

json.dump(
    {"box": [UX0, UY0, UX1, UY1], "levels": LEVELS, "size": [w, h]},
    open(BLINK_DIR / "blink.json", "w"),
    indent=2,
)
print("saved", len(LEVELS), "frames ->", BLINK_DIR)
