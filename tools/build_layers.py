"""把立绘拆成可独立动画的图层：身体 / 头发 / 眼睛。

思路：
1. 从原始 3900px 立绘重出 2 倍分辨率素材（运行时降采样，边缘更锐利）
2. 颜色分割出头发（金发），得到软遮罩
3. 身体层挖掉头发，被遮住的区域用最近邻填充（露出量只有几像素，够用）
4. 标定眼睛包围盒，生成闭眼图层
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

SRC = Path(r"C:\Users\Administrator\Desktop\星璃Hoshiri\立绘2.jpeg")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "out" / "hd"
OUT.mkdir(parents=True, exist_ok=True)

TARGET_H = 840          # 2 倍于当前的 420
CROP_RATIO = 0.42       # 与 pet_edge_42 一致
WHITE_THRESH = 244
WORK_W = 2400


def cutout_alpha(img: Image.Image) -> Image.Image:
    """去掉纯白背景，返回 alpha 通道（全分辨率）。"""
    w, h = img.size
    scale = WORK_W / w
    small = img.resize((WORK_W, max(1, int(h * scale))), Image.LANCZOS)
    arr = np.asarray(small).astype(np.int16)
    white = arr.min(axis=2) >= WHITE_THRESH

    labels, n = ndimage.label(white)
    if n:
        border = np.unique(
            np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
        )
        border = border[border != 0]
        bg = np.isin(labels, border)
    else:
        bg = np.zeros(white.shape, bool)

    mask = ~bg
    mask = ndimage.binary_erosion(mask, iterations=1)
    alpha = Image.fromarray((mask * 255).astype(np.uint8), "L")
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    return alpha.resize((w, h), Image.LANCZOS)


def hair_soft_mask(rgba: np.ndarray) -> np.ndarray:
    """金发的软遮罩，0..1。"""
    r = rgba[..., 0].astype(np.float32)
    g = rgba[..., 1].astype(np.float32)
    b = rgba[..., 2].astype(np.float32)
    mx = rgba[..., :3].max(axis=2).astype(np.float32)
    mn = rgba[..., :3].min(axis=2).astype(np.float32)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)

    # 金发：偏暖（R 明显大于 B）、够亮、有一定饱和
    warm = (r - b)
    score = np.clip((warm - 18) / 40, 0, 1) * np.clip((sat - 0.12) / 0.18, 0, 1)
    score *= np.clip((mx - 90) / 80, 0, 1)

    mask = score > 0.35
    mask = ndimage.binary_opening(mask, np.ones((3, 3)))
    mask = ndimage.binary_closing(mask, np.ones((5, 5)))
    mask = ndimage.binary_fill_holes(mask)
    # 去掉零星小块
    lab, n = ndimage.label(mask)
    if n:
        sizes = ndimage.sum(mask, lab, range(1, n + 1))
        keep = np.isin(lab, np.where(sizes > 400)[0] + 1)
        mask = keep
    soft = ndimage.gaussian_filter(mask.astype(np.float32), 1.2)
    return np.clip(soft, 0, 1)


def nearest_fill(rgb: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """把无效区域的像素用最近的已知像素填补。"""
    if valid.all():
        return rgb
    idx = ndimage.distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return rgb[idx[0], idx[1]]


def main() -> None:
    print("读取原图 ...")
    src = Image.open(SRC).convert("RGB")
    alpha = cutout_alpha(src)
    rgba = src.convert("RGBA")
    rgba.putalpha(alpha)

    # 裁掉下方，保留上半身
    bbox = rgba.getbbox()
    rgba = rgba.crop(bbox)
    cut_h = int(rgba.height * CROP_RATIO)
    part = rgba.crop((0, 0, rgba.width, cut_h))

    # 底部渐隐
    fade = int(part.height * 0.06)
    a = np.asarray(part.getchannel("A")).astype(np.float32)
    ramp = np.ones(a.shape[0], np.float32)
    ramp[-fade:] = np.linspace(1.0, 0.0, fade)
    a = a * ramp[:, None]
    part.putalpha(Image.fromarray(a.astype(np.uint8), "L"))

    # 统一高度到 TARGET_H
    scale = TARGET_H / part.height
    base = part.resize((int(part.width * scale), TARGET_H), Image.LANCZOS)
    base.save(OUT / "base.png")
    print("base:", base.size)

    arr = np.asarray(base).astype(np.float32)
    rgb = arr[..., :3]
    alpha_arr = arr[..., 3] / 255.0

    # 头发遮罩
    soft = hair_soft_mask(arr.astype(np.uint8)) * alpha_arr
    soft[alpha_arr < 0.05] = 0

    hair = arr.copy()
    hair[..., 3] = (soft * 255).astype(np.float32)
    Image.fromarray(hair.clip(0, 255).astype(np.uint8), "RGBA").save(OUT / "hair.png")
    print("hair 覆盖率: %.1f%%" % (100 * (soft > 0.5).sum() / max((alpha_arr > 0.5).sum(), 1)))

    # 身体：挖掉头发，再用最近邻补齐
    body_alpha = alpha_arr * (1 - soft)
    body_rgb = nearest_fill(rgb, alpha_arr > 0.05)
    body = np.dstack([body_rgb, (body_alpha * 255)]).clip(0, 255).astype(np.uint8)
    Image.fromarray(body, "RGBA").save(OUT / "body.png")
    print("body saved")

    # 发色底衬：挡住头发位移后露出的空洞
    # 用重度模糊的底图取色，再裁成头发形状，露出来的是一条平滑的金色带
    blurred = np.asarray(
        Image.fromarray(rgb.clip(0, 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(10)),
        dtype=np.float32,
    )
    base_mask = ndimage.binary_dilation(soft > 0.35, iterations=3)
    base_alpha = ndimage.gaussian_filter(base_mask.astype(np.float32), 1.0) * alpha_arr
    hairbase = np.dstack([blurred, base_alpha * 255]).clip(0, 255).astype(np.uint8)
    Image.fromarray(hairbase, "RGBA").save(OUT / "hairbase.png")
    print("hairbase saved")

    # 供目视检查的叠加预览：身体红、头发蓝
    dbg = np.zeros_like(arr)
    dbg[..., 0] = body_alpha * 255
    dbg[..., 2] = soft * 255
    dbg[..., 3] = 255
    Image.fromarray(dbg.clip(0, 255).astype(np.uint8), "RGBA").save(OUT / "_debug_split.png")
    print("debug saved")


if __name__ == "__main__":
    main()

