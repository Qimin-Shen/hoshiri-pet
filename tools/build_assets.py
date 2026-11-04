"""把原始立绘处理成桌宠可用的透明素材。

流程：白底分割 -> 抠图 -> 羽化 -> 裁掉下半身 -> 等比缩放
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "assets" / "raw"
OUT = ROOT / "assets" / "out"
OUT.mkdir(parents=True, exist_ok=True)

SRC = Path(r"C:\Users\Administrator\Desktop\星璃Hoshiri\立绘2.jpeg")


def cutout(img: Image.Image, work_w: int = 1400, white_thresh: int = 244) -> Image.Image:
    """把纯白背景去掉，返回带 alpha 的图。"""
    img = img.convert("RGB")
    w, h = img.size
    scale = work_w / w
    small = img.resize((work_w, max(1, int(h * scale))), Image.LANCZOS)

    arr = np.asarray(small).astype(np.int16)
    # 白色背景：三通道都很亮
    white = (arr.min(axis=2) >= white_thresh)

    # 只保留与画布边缘连通的白，避免把裙子高光也挖掉
    labels, n = ndimage.label(white)
    if n == 0:
        alpha_small = np.full(white.shape, 255, np.uint8)
    else:
        border_ids = np.unique(
            np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
        )
        border_ids = border_ids[border_ids != 0]
        bg = np.isin(labels, border_ids)
        alpha_small = np.where(bg, 0, 255).astype(np.uint8)

    # 轻微收缩 1px 再用高斯羽化，去掉白边
    alpha_small = ndimage.binary_erosion(alpha_small > 0, iterations=1)
    alpha_small = (alpha_small * 255).astype(np.uint8)
    alpha_img = Image.fromarray(alpha_small, "L").filter(ImageFilter.GaussianBlur(0.8))

    # 放大回原分辨率
    alpha_full = alpha_img.resize((w, h), Image.LANCZOS)

    rgba = img.convert("RGBA")
    rgba.putalpha(alpha_full)
    return rgba


def trim(img: Image.Image, pad: int = 4) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l, t = max(0, l - pad), max(0, t - pad)
    r, b = min(img.width, r + pad), min(img.height, b + pad)
    return img.crop((l, t, r, b))


def build() -> None:
    if not SRC.exists():
        sys.exit(f"找不到源图: {SRC}")

    print(f"读取 {SRC.name} ...")
    src = Image.open(SRC)
    print(f"  原始尺寸 {src.size}")

    cut = cutout(src)
    cut = trim(cut)
    print(f"  抠图后 {cut.size}")

    cut.save(OUT / "full.png")
    print("  -> full.png")

    # 半身：只保留上部，用于“趴在边框上”的效果
    for ratio, name in ((0.50, "pet_edge_50"), (0.42, "pet_edge_42"), (0.58, "pet_edge_58")):
        h = int(cut.height * ratio)
        part = cut.crop((0, 0, cut.width, h))

        # 底部做一点渐隐，避免生硬的切断线
        fade = 46
        alpha = np.asarray(part.getchannel("A")).astype(np.float32)
        ramp = np.ones(alpha.shape[0], np.float32)
        ramp[-fade:] = np.linspace(1.0, 0.0, fade)
        alpha = alpha * ramp[:, None]
        part.putalpha(Image.fromarray(alpha.astype(np.uint8), "L"))

        target_h = 420
        w = int(part.width * target_h / part.height)
        part = part.resize((w, target_h), Image.LANCZOS)
        part.save(OUT / f"{name}.png")
        print(f"  -> {name}.png  {part.size}")

    # 头像：给托盘和对话气泡用
    avatar_src = Path(r"C:\Users\Administrator\Desktop\星璃Hoshiri\头像喵.jpeg")
    if avatar_src.exists():
        a = Image.open(avatar_src).convert("RGB")
        side = min(a.size)
        a = a.crop(
            ((a.width - side) // 2, (a.height - side) // 2,
             (a.width + side) // 2, (a.height + side) // 2)
        ).resize((256, 256), Image.LANCZOS)

        mask = Image.new("L", (256, 256), 0)
        from PIL import ImageDraw
        ImageDraw.Draw(mask).ellipse((0, 0, 255, 255), fill=255)
        a.putalpha(mask)
        a.save(OUT / "avatar.png")
        print("  -> avatar.png  256x256")

    print("完成")


if __name__ == "__main__":
    build()
