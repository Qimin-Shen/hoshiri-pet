"""星屑 / 月牙粒子，纯程序化绘制，不占素材。"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath

NO_PEN = Qt.PenStyle.NoPen


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "size", "phase", "life", "max_life", "kind")

    def __init__(self, w: int, h: int, initial: bool = True) -> None:
        self.reset(w, h, initial)

    def reset(self, w: int, h: int, initial: bool = False) -> None:
        self.x = random.uniform(0, w)
        self.y = random.uniform(h * 0.05, h) if initial else random.uniform(h * 0.55, h)
        self.vx = random.uniform(-0.25, 0.25)
        self.vy = random.uniform(-0.55, -0.15)
        self.size = random.uniform(3.0, 7.5)
        self.phase = random.uniform(0, math.tau)
        self.max_life = random.uniform(180, 420)
        self.life = random.uniform(0, self.max_life) if initial else 0.0
        self.kind = random.choices(("star", "dot", "moon"), weights=(6, 3, 1))[0]


def draw_star(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    path = QPainterPath()
    path.moveTo(cx, cy - r)
    path.quadTo(cx + r * 0.18, cy - r * 0.18, cx + r, cy)
    path.quadTo(cx + r * 0.18, cy + r * 0.18, cx, cy + r)
    path.quadTo(cx - r * 0.18, cy + r * 0.18, cx - r, cy)
    path.quadTo(cx - r * 0.18, cy - r * 0.18, cx, cy - r)
    p.setBrush(color)
    p.setPen(NO_PEN)
    p.drawPath(path)


def draw_moon(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    full = QPainterPath()
    full.addEllipse(QPointF(cx, cy), r, r)
    cut = QPainterPath()
    cut.addEllipse(QPointF(cx + r * 0.55, cy - r * 0.25), r * 0.9, r * 0.9)
    p.setBrush(color)
    p.setPen(NO_PEN)
    p.drawPath(full.subtracted(cut))


class ParticleField:
    def __init__(self, count: int = 14) -> None:
        self.items: list[Particle] = []
        self.count = count
        self.w = 0
        self.h = 0

    def resize(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        while len(self.items) < self.count:
            self.items.append(Particle(w, h))
        for p in self.items:
            p.x = min(p.x, w)
            p.y = min(p.y, h)

    def tick(self, dt: float = 1.0) -> None:
        for p in self.items:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.phase += 0.05 * dt
            p.life += dt
            if p.life > p.max_life or p.y < self.h * 0.02:
                p.reset(self.w, self.h)

    def paint(self, painter: QPainter, accent: QColor, gold: QColor) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for p in self.items:
            ratio = p.life / p.max_life
            fade = min(1.0, ratio * 6, (1 - ratio) * 6)
            if fade <= 0:
                continue
            twinkle = 0.65 + 0.35 * math.sin(p.phase * 2.2)
            c = QColor(gold if p.kind == "moon" else accent)
            c.setAlphaF(max(0.0, min(1.0, fade * twinkle * 0.85)))
            r = p.size * (0.85 + 0.15 * twinkle)
            if p.kind == "star":
                draw_star(painter, p.x, p.y, r, c)
            elif p.kind == "moon":
                draw_moon(painter, p.x, p.y, r * 0.9, c)
            else:
                painter.setBrush(c)
                painter.setPen(NO_PEN)
                painter.drawEllipse(QPointF(p.x, p.y), r * 0.42, r * 0.42)
