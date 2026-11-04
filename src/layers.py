"""角色分层渲染：身体 / 发色底衬 / 头发（逐像素行位移）/ 眨眼序列。

头发每帧做一次亚像素级的逐行插值位移：先把左右各补一列全透明，
这样越界采样天然得到透明，省掉掩码和裁剪。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap

HAIR_SHIFT = 12.0      # 屏幕上发梢最大位移（px）
WAVE_K = 0.0042        # 行波密度
ROT_DEG = 1.6          # 头发整体旋转幅度
ROT_SPEED = 2 * math.pi / 9.5


class Character:
    def __init__(self, folder: Path) -> None:
        self.body = QPixmap(str(folder / "body.png"))
        self.hairbase = QPixmap(str(folder / "hairbase.png"))
        self._hair_pm = QPixmap(str(folder / "hair.png"))

        missing = [n for n, p in (
            ("body", self.body), ("hairbase", self.hairbase), ("hair", self._hair_pm)
        ) if p.isNull()]
        if missing:
            raise SystemExit(f"缺少图层：{missing}，先运行 tools/build_layers.py")

        self.w = self.body.width()
        self.h = self.body.height()

        self.blink_frames: list[QPixmap] = []
        self.blink_box: QRectF | None = None
        meta_path = folder / "blink" / "blink.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text("utf-8"))
            for i in range(1, 11):
                pm = QPixmap(str(folder / "blink" / f"p{i:02d}.png"))
                if not pm.isNull():
                    self.blink_frames.append(pm)
            if self.blink_frames:
                self.blink_box = QRectF(*meta["box"])

        self._cache: tuple | None = None
        self._body_scaled = QPixmap()
        self._hairbase_scaled = QPixmap()

    # ---------- 预处理 ----------

    def _prepare(self, w: int, h: int) -> None:
        if self._cache and self._cache[0] == (w, h):
            return

        mode = (Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._body_scaled = self.body.scaled(w, h, *mode)
        self._hairbase_scaled = self.hairbase.scaled(w, h, *mode)

        img = self._hair_pm.scaled(w, h, *mode).toImage().convertToFormat(
            QImage.Format.Format_RGBA8888
        )
        bpl = img.bytesPerLine()
        arr = np.frombuffer(bytes(img.constBits()), np.uint8).reshape(img.height(), bpl)
        arr = arr[:, : w * 4].reshape(h, w, 4).astype(np.float32)

        # 位移最大可达 HAIR_SHIFT + 拖拽惯性，两侧留足空档，越界自然取到全透明
        self._pad = int(HAIR_SHIFT + 40)
        self._padded = np.pad(arr, ((0, 0), (self._pad, self._pad), (0, 0)))
        self._out = np.empty((h, w, 4), np.float32)
        self._rows = np.arange(h)[:, None]
        self._xs = np.arange(w, dtype=np.float32)[None, :]
        self._ys = np.arange(h, dtype=np.float32)

        self._img = QImage(w, h, QImage.Format.Format_RGBA8888)
        self._view_bpl = self._img.bytesPerLine()
        self._view = np.frombuffer(self._img.bits(), np.uint8).reshape(h, self._view_bpl)

        self._cache = ((w, h),)

    # ---------- 绘制 ----------

    def draw(
        self,
        p: QPainter,
        target: QRectF,
        t: float,
        blink: float = 0.0,
        drag: float = 0.0,
    ) -> None:
        tw, th = int(target.width()), int(target.height())
        self._prepare(tw, th)

        p.save()
        p.translate(target.x(), target.y())

        p.drawPixmap(0, 0, self._body_scaled)
        p.drawPixmap(0, 0, self._hairbase_scaled)

        anchor = QPointF(tw * 0.52, th * 0.27)
        angle = ROT_DEG * math.sin(t * ROT_SPEED)
        swing = 0.85 + 0.15 * math.sin(t * 0.37)

        p.save()
        p.translate(anchor)
        p.rotate(angle)
        p.translate(-anchor)
        p.drawImage(0, 0, self._warp_hair(t, swing, drag))
        p.restore()

        if blink > 0 and self.blink_frames and self.blink_box is not None:
            idx = min(len(self.blink_frames) - 1, max(0, int(blink * len(self.blink_frames)) - 1))
            p.drawPixmap(self.blink_box.topLeft(), self.blink_frames[idx])

        p.restore()

    def _warp_hair(self, t: float, swing: float, drag: float) -> QImage:
        h, w, _ = self._out.shape
        ys = self._ys
        ratio = (ys / h) ** 1.9
        dx = HAIR_SHIFT * ratio * swing * np.sin(t * 0.62 + ys * WAVE_K) + drag * ratio

        xs = self._xs - dx[:, None]
        x0 = np.floor(xs)
        frac = xs - x0
        i0 = np.clip(x0.astype(np.int32) + self._pad, 0, self._padded.shape[1] - 2)
        i1 = i0 + 1

        rows = self._rows
        out = self._out
        pad = self._padded
        for c in range(4):
            ch = pad[:, :, c]
            out[:, :, c] = ch[rows, i0] * (1 - frac) + ch[rows, i1] * frac

        np.clip(out, 0, 255, out=out)
        self._view[:, : w * 4] = out.astype(np.uint8).reshape(h, w * 4)
        return self._img

    def size(self) -> tuple[int, int]:
        return self.w, self.h
