"""点击爆散、拖拽拖尾、光晕等特效。"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QRadialGradient

NO_PEN = Qt.PenStyle.NoPen


def star_path(cx: float, cy: float, r: float) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(cx, cy - r)
    path.quadTo(cx + r * 0.2, cy - r * 0.2, cx + r, cy)
    path.quadTo(cx + r * 0.2, cy + r * 0.2, cx, cy + r)
    path.quadTo(cx - r * 0.2, cy + r * 0.2, cx - r, cy)
    path.quadTo(cx - r * 0.2, cy - r * 0.2, cx, cy - r)
    return path


class Bit:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "kind", "color")

    def __init__(self, x, y, vx, vy, life, size, kind, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life, self.max_life = 0.0, life
        self.size = size
        self.kind = kind
        self.color = color


class Effects:
    def __init__(self) -> None:
        self.bits: list[Bit] = []

    def clear(self) -> None:
        self.bits.clear()

    def burst(self, x: float, y: float, n: int = 16) -> None:
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(1.2, 4.2)
            self.bits.append(Bit(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd - 0.6,
                random.uniform(0.55, 1.1),
                random.uniform(2.5, 6.0),
                random.choice(("star", "dot")),
                QColor(random.choice(("#FFE9A8", "#A9C9F2", "#FFFFFF"))),
            ))

    def trail(self, x: float, y: float, vx: float) -> None:
        if random.random() > 0.55:
            return
        self.bits.append(Bit(
            x + random.uniform(-6, 6), y + random.uniform(-10, 10),
            -vx * 0.12 + random.uniform(-0.3, 0.3), random.uniform(-0.4, 0.1),
            random.uniform(0.35, 0.7),
            random.uniform(1.5, 3.6),
            "dot",
            QColor("#BFD9FF"),
        ))

    def tick(self, dt: float = 1 / 60) -> None:
        alive: list[Bit] = []
        for b in self.bits:
            b.life += dt
            if b.life >= b.max_life:
                continue
            b.x += b.vx
            b.y += b.vy
            b.vy += 0.06      # 轻微重力
            b.vx *= 0.97
            alive.append(b)
        self.bits = alive

    def paint(self, p: QPainter) -> None:
        if not self.bits:
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(NO_PEN)
        for b in self.bits:
            k = 1 - b.life / b.max_life
            c = QColor(b.color)
            c.setAlphaF(max(0.0, min(1.0, k)))
            p.setBrush(c)
            if b.kind == "star":
                p.drawPath(star_path(b.x, b.y, b.size * (0.6 + 0.4 * k)))
            else:
                p.drawEllipse(QPointF(b.x, b.y), b.size * 0.45 * k + 0.6, b.size * 0.45 * k + 0.6)


def paint_glow(p: QPainter, cx: float, cy: float, radius: float, pulse: float) -> None:
    """角色背后的柔光，随呼吸脉动。"""
    r = radius * (0.94 + 0.08 * pulse)
    grad = QRadialGradient(QPointF(cx, cy), r)
    grad.setColorAt(0.0, QColor(150, 190, 255, 46))
    grad.setColorAt(0.55, QColor(140, 180, 245, 20))
    grad.setColorAt(1.0, QColor(140, 180, 245, 0))
    p.setPen(NO_PEN)
    p.setBrush(grad)
    p.drawEllipse(QPointF(cx, cy), r, r * 0.85)
