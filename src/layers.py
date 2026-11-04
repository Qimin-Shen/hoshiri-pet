"""角色分层渲染：身体 / 发色底衬 / 头发（逐行错位摆动）/ 闭眼。"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap

SLICE = 10          # 头发按 10px 一行切开做错位
HAIR_MAX_SHIFT = 15  # 源图坐标下的最大横向位移


class Character:
    def __init__(self, folder: Path) -> None:
        self.body = QPixmap(str(folder / "body.png"))
        self.hairbase = QPixmap(str(folder / "hairbase.png"))
        self.hair = QPixmap(str(folder / "hair.png"))
        self.eyes_closed = QPixmap(str(folder / "eyes_closed.png"))

        missing = [n for n, p in (
            ("body", self.body), ("hairbase", self.hairbase), ("hair", self.hair)
        ) if p.isNull()]
        if missing:
            raise SystemExit(f"缺少图层：{missing}，先运行 tools/build_layers.py")

        self.w = self.body.width()
        self.h = self.body.height()

    # ---------- 绘制 ----------

    def draw(self, p: QPainter, target: QRectF, t: float, blink: bool, drag: float = 0.0) -> None:
        """target 为角色右下角锚定的矩形。"""
        scale_x = target.width() / self.w
        scale_y = target.height() / self.h

        p.save()
        p.translate(target.x(), target.y())
        p.scale(scale_x, scale_y)

        p.drawPixmap(0, 0, self.body)
        p.drawPixmap(0, 0, self.hairbase)

        # 头发：逐行水平错位，越靠近发梢幅度越大
        phase = t * 1.15
        for y in range(0, self.h, SLICE):
            ratio = min(1.0, y / self.h)
            amp = HAIR_MAX_SHIFT * (ratio ** 1.9)
            dx = amp * math.sin(phase + y * 0.011)
            # 拖拽时的惯性甩动
            dx += drag * (ratio ** 1.6)
            src = QRectF(0, y, self.w, SLICE)
            p.drawPixmap(QPointF(dx, y), self.hair, src)

        if blink and not self.eyes_closed.isNull():
            p.drawPixmap(0, 0, self.eyes_closed)

        p.restore()

    def size(self) -> tuple[int, int]:
        return self.w, self.h
