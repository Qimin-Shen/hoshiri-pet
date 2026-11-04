"""输入框：双击桌宠后浮出，Enter 发送，Esc 收起。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QLineEdit, QWidget


class _Edit(QLineEdit):
    escaped = Signal()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.escaped.emit()
            return
        super().keyPressEvent(event)


class ChatInput(QWidget):
    submitted = Signal(str)

    WIDTH = 320
    HEIGHT = 44

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self.edit = _Edit(self)
        self.edit.setPlaceholderText("跟星璃说点什么…")
        self.edit.setFont(QFont("Microsoft YaHei UI", 10))
        self.edit.setStyleSheet(
            "QLineEdit{background:transparent;border:none;color:#2B4C8C;"
            "selection-background-color:#A9C9F2;padding-left:14px;}"
        )
        self.edit.setGeometry(6, 4, self.WIDTH - 12, self.HEIGHT - 8)
        self.edit.returnPressed.connect(self._submit)
        self.edit.escaped.connect(self.hide)
        self.hide()

    def _submit(self) -> None:
        text = self.edit.text().strip()
        if not text:
            return
        self.edit.clear()
        self.submitted.emit(text)

    def open_at(self, anchor: QWidget) -> None:
        geo = anchor.frameGeometry()
        x = geo.center().x() - self.width() // 2
        y = geo.top() + 90 - self.height() - 4
        screen = self.screen().availableGeometry() if self.screen() else geo
        x = max(screen.left() + 6, min(x, screen.right() - self.width() - 6))
        self.move(QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()
        self.edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def follow(self, anchor: QWidget) -> None:
        if self.isVisible():
            geo = anchor.frameGeometry()
            self.move(QPoint(geo.center().x() - self.width() // 2, geo.top() + 90 - self.height() - 4))

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor(169, 201, 242, 230), 1.3))
        p.setBrush(QColor(255, 255, 255, 245))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
        p.end()
