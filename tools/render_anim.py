"""离屏渲染角色动画帧，不弹窗口，用于检查头发摆动效果。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from layers import Character

app = QApplication([])
char = Character(Path(__file__).resolve().parent.parent / "assets" / "out" / "hd")

W, H = 520, 360
cyc = [0.0, 0.55, 1.1, 1.65]

frames = []
for t in cyc:
    img = QImage(W, H, QImage.Format.Format_ARGB32)
    img.fill(QColor("#16203a"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    cw = char.w * (H - 20) / char.h
    rect = QRectF((W - cw) / 2, 10, cw, H - 20)
    char.draw(p, rect, t, blink=(t == 1.1))
    p.end()
    frames.append(img)
    img.save(str(Path(__file__).resolve().parent.parent / "docs" / f"_anim_{t:.2f}.png"))

print("rendered", len(frames), "frames")
