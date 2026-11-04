"""合成闭眼：只去除虹膜与眼白，保留眼睑和睫毛，局部肤色修补。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

OUT = Path(__file__).resolve().parent.parent / "assets" / "out" / "hd"
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

PAD = 6
EYES = [(max(0, x0 - PAD), max(0, y0 - PAD), min(w, x1 + PAD), min(h, y1 + PAD)) for x0, y0, x1, y1 in boxes]
print("eyes:", EYES)

out = np.asarray(base).copy()


def skin_rows(patch: np.ndarray, which: str) -> np.ndarray:
    rows = patch[:2] if which == "top" else patch[-2:]
    return rows.reshape(-1, 4).mean(axis=0)


for (x0, y0, x1, y1) in EYES:
    sub = arr[y0:y1, x0:x1]
    sr, sg, sb, sa = sub[..., 0], sub[..., 1], sub[..., 2], sub[..., 3]

    # 眼白 + 虹膜：偏蓝，或非常亮且靠中间
    bluish = sb > sr + 12
    bright = (sr > 232) & (sg > 232) & (sb > 232)
    ys, xs = np.mgrid[0: sub.shape[0], 0: sub.shape[1]]
    center = ((xs - sub.shape[1] / 2) ** 2 / (sub.shape[1] ** 2) +
              (ys - sub.shape[0] / 2) ** 2 / (sub.shape[0] ** 2)) < 0.30
    mask = (bluish | (bright & center)) & (sa > 200)

    mask = ndimage.binary_closing(mask, np.ones((3, 3)))
    mask = ndimage.binary_dilation(mask, iterations=1)
    soft = ndimage.gaussian_filter(mask.astype(np.float32), 1.6)

    top = skin_rows(sub, "top")
    bot = skin_rows(sub, "bot")
    t = np.linspace(0, 1, sub.shape[0])[:, None, None]
    fill = top.reshape(1, 1, 4) * (1 - t) + bot.reshape(1, 1, 4) * t

    mixed = sub * (1 - soft[..., None]) + fill * soft[..., None]
    out[y0:y1, x0:x1] = mixed

# 补一条闭眼线，避免看起来只是「没有眼睛」
from PIL import ImageDraw, ImageFilter

line = Image.new("RGBA", (w, h), (0, 0, 0, 0))
ld = ImageDraw.Draw(line)
for (x0, y0, x1, y1) in EYES:
    W, H = x1 - x0, y1 - y0
    cy = y0 + H * 0.56
    pts = [
        (x0 + W * 0.14, cy - H * 0.06),
        (x0 + W * 0.35, cy + H * 0.10),
        (x0 + W * 0.65, cy + H * 0.10),
        (x0 + W * 0.86, cy - H * 0.06),
    ]
    ld.line(pts, fill=(122, 84, 70, 210), width=2, joint="curve")
line = line.filter(ImageFilter.GaussianBlur(0.7))
line_arr = np.asarray(line).astype(np.float32)
out = out.astype(np.float32)
la = line_arr[..., 3:4] / 255.0
out[..., :3] = out[..., :3] * (1 - la) + line_arr[..., :3] * la
out = out.clip(0, 255)

closed = np.dstack([out[..., :3], arr[..., 3]]).clip(0, 255).astype(np.uint8)
Image.fromarray(closed, "RGBA").save(OUT / "eyes_closed.png")

# 预览
comp = Image.alpha_composite(base, Image.open(OUT / "eyes_closed.png").convert("RGBA"))
box = (620, 270, 800, 380)
comp.crop(box).resize(((box[2] - box[0]) * 3, (box[3] - box[1]) * 3), Image.LANCZOS).save(
    OUT / "_iris_fill.png"
)

json.dump({"eyes": EYES, "size": [w, h]}, open(OUT / "eyes.json", "w"), indent=2)
print("saved")

