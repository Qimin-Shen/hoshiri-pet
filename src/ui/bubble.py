"""对话气泡：浮在桌宠头顶，流式追加文字。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QWidget

MAX_W = 300
PAD = 13
TAIL = 9

TEXT_COLOR = "#2B4C8C"
BORDER = QColor(169, 201, 242, 220)
FILL = QColor(255, 255, 255, 238)


class SpeechBubble(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Microsoft YaHei UI", 10))
        self.label.setStyleSheet(f"color:{TEXT_COLOR}; background:transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.hide()

    # ---------- 内容 ----------

    def set_text(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            self.hide()
            return
        self.label.setText(text)
        self._fit(text)
        self.show()
        self.raise_()

    def _fit(self, text: str) -> None:
        fm = QFontMetrics(self.label.font())
        rect = fm.boundingRect(
            QRect(0, 0, MAX_W - PAD * 2, 10_000),
            int(Qt.TextFlag.TextWordWrap),
            text,
        )
        text_w = max(60, min(MAX_W - PAD * 2, rect.width()))
        text_h = rect.height()

        width = text_w + PAD * 2
        height = text_h + PAD * 2 + TAIL
        self.setFixedSize(width, height)
        self.label.setGeometry(PAD, PAD, text_w, text_h)

    # ---------- 位置 ----------

    def follow(self, anchor: QWidget, gap: int = 6) -> None:
        if not self.isVisible():
            return
        geo = anchor.frameGeometry()
        x = geo.center().x() - self.width() // 2
        y = geo.top() + 88 - self.height() - gap
        self.move(QPoint(x, y))

    # ---------- 绘制 ----------

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        body = QRect(0, 0, self.width(), self.height() - TAIL)
        path = QPainterPath()
        path.addRoundedRect(body, 13, 13)

        tail = QPainterPath()
        cx = self.width() / 2
        tail.moveTo(cx - 8, body.bottom() - 1)
        tail.lineTo(cx + 2, body.bottom() + TAIL)
        tail.lineTo(cx + 8, body.bottom() - 1)
        tail.closeSubpath()

        p.setPen(QPen(BORDER, 1.2))
        p.setBrush(FILL)
        p.drawPath(path.united(tail))
        p.end()
