"""额度面板：毛玻璃卡片 + 余额环 + 指标 + 近 7 天柱状图。"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QRectF,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QConicalGradient, QFont, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

CARD_W = 300
INK = "#2B4C8C"
MUTED = "#7C99BC"
ACCENT = "#2B6FD6"
GOLD = "#D9AE55"
TRACK = QColor(226, 236, 249)
BORDER = QColor(150, 186, 235, 120)
FILL = QColor(255, 255, 255, 240)


class Ring(QWidget):
    """余额余量环。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(78, 78)
        self._shown = 0.0

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(520)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_value)

    def _on_value(self, v) -> None:
        self._shown = float(v)
        self.update()

    def set_ratio(self, ratio: float) -> None:
        ratio = max(0.0, min(1.0, ratio))
        self._anim.stop()
        self._anim.setStartValue(self._shown)
        self._anim.setEndValue(ratio)
        self._anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(7, 7, self.width() - 14, self.height() - 14)

        pen = QPen(TRACK, 7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)

        if self._shown > 0.001:
            grad = QConicalGradient(rect.center(), 90)
            grad.setColorAt(0.0, QColor(ACCENT))
            grad.setColorAt(0.55, QColor("#6FA8F0"))
            grad.setColorAt(1.0, QColor(GOLD))
            pen = QPen(grad, 7)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(rect, 90 * 16, -int(360 * 16 * self._shown))

        p.setPen(QColor(INK))
        p.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.DemiBold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{int(self._shown * 100)}%")
        p.end()


class BarChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.values: list[tuple[str, int]] = []
        self.setFixedHeight(58)

    def set_values(self, values: list[tuple[str, int]]) -> None:
        """固定 7 个槽位，从右往左填，早期数据少时左边留空。"""
        tail = values[-7:]
        pad = 7 - len(tail)
        self.values = [("", 0)] * pad + tail
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if not self.values:
            p.setPen(QColor(MUTED))
            p.setFont(QFont("Microsoft YaHei UI", 8))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "暂无记录")
            p.end()
            return

        n = 7
        gap = 8
        bar_w = min(30.0, max(8.0, (self.width() - gap * (n - 1)) / n))
        total_w = n * bar_w + (n - 1) * gap
        offset = max(0.0, (self.width() - total_w) / 2)
        peak = max((v for _, v in self.values), default=0) or 1
        base = self.height() - 6

        for i, (_day, v) in enumerate(self.values):
            if v <= 0:
                continue
            h = 3 + (base - 10) * (v / peak)
            x = offset + i * (bar_w + gap)
            last = i == n - 1
            c = QColor(GOLD if last else ACCENT)
            c.setAlpha(235 if last else 150)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x, base - h, bar_w, h), 4, 4)

        p.setPen(QColor(MUTED))
        p.setFont(QFont("Microsoft YaHei UI", 7))
        p.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            "近 7 天",
        )
        p.end()


class Dashboard(QWidget):
    refresh_requested = Signal()
    settings_requested = Signal()

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
        self.setFixedWidth(CARD_W)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(6)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color:{ACCENT}; font-size:9px; background:transparent;")
        self.state = QLabel("未绑定 API Key")
        self.state.setFont(QFont("Microsoft YaHei UI", 8))
        self.state.setStyleSheet(f"color:{MUTED}; background:transparent;")
        head.addWidget(self.dot)
        head.addWidget(self.state)
        head.addStretch(1)
        self.updated = QLabel("")
        self.updated.setFont(QFont("Microsoft YaHei UI", 8))
        self.updated.setStyleSheet(f"color:{MUTED}; background:transparent;")
        head.addWidget(self.updated)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(8)
        left = QVBoxLayout()
        left.setSpacing(0)
        self.balance = QLabel("--")
        self.balance.setFont(QFont("Microsoft YaHei UI", 27, QFont.Weight.DemiBold))
        self.balance.setStyleSheet(f"color:{INK}; background:transparent;")
        left.addWidget(self.balance)
        cap = QLabel("DeepSeek 余额")
        cap.setFont(QFont("Microsoft YaHei UI", 8))
        cap.setStyleSheet(f"color:{MUTED}; background:transparent;")
        left.addWidget(cap)
        body.addLayout(left)
        body.addStretch(1)
        self.ring = Ring(self)
        body.addWidget(self.ring)
        root.addLayout(body)

        root.addWidget(self._line())

        self.today_cost = self._stat_row(root, "今日花费")
        self.today_tokens = self._stat_row(root, "今日 tokens")
        self.total_tokens = self._stat_row(root, "累计 tokens")

        root.addWidget(self._line())

        self.chart = BarChart(self)
        root.addWidget(self.chart)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 2, 0, 0)
        bottom.addStretch(1)
        btn_style = (
            "QPushButton{background:transparent;border:none;color:%s;font-size:11px;"
            "padding:3px 6px;}"
            "QPushButton:hover{color:%s;}"
        ) % (ACCENT, GOLD)

        self.btn_settings = QPushButton("设置")
        self.btn_settings.setStyleSheet(btn_style)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.settings_requested)
        bottom.addWidget(self.btn_settings)

        btn_refresh = QPushButton("刷新")
        btn_refresh.setStyleSheet(btn_style)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_requested)
        bottom.addWidget(btn_refresh)
        root.addLayout(bottom)

        self.hide()

    def _line(self) -> QWidget:
        line = QWidget(self)
        line.setFixedHeight(1)
        line.setStyleSheet("background:rgba(160,192,235,60);")
        return line

    def _stat_row(self, layout: QVBoxLayout, label: str) -> QLabel:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        name = QLabel(label)
        name.setFont(QFont("Microsoft YaHei UI", 9))
        name.setStyleSheet(f"color:{MUTED}; background:transparent;")
        value = QLabel("--")
        value.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Medium))
        value.setStyleSheet(f"color:{INK}; background:transparent;")
        value.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(name)
        row.addStretch(1)
        row.addWidget(value)
        layout.addLayout(row)
        return value

    # ---------- 数据 ----------

    def update_data(
        self,
        balance: float | None,
        currency: str,
        today_cost: float,
        today_tokens: int,
        total_tokens: int,
        history: list[tuple[str, int]],
        updated_at: str,
        reference: float | None = None,
    ) -> None:
        if balance is None:
            self.balance.setText("--")
            self.ring.set_ratio(0)
        else:
            symbol = "¥" if currency.upper() in ("CNY", "RMB") else "$"
            self.balance.setText(f"{symbol}{balance:,.2f}")
            ref = reference or max(balance, 1.0)
            self.ring.set_ratio(balance / ref if ref else 0)

        self.today_cost.setText(f"¥{today_cost:.2f}")
        self.today_tokens.setText(f"{today_tokens:,}")
        self.total_tokens.setText(f"{total_tokens:,}")
        self.chart.set_values(history)
        self.updated.setText(updated_at)

    def set_state(self, text: str, ok: bool = True) -> None:
        self.state.setText(text)
        self.dot.setStyleSheet(
            f"color:{ACCENT if ok else '#C0392B'}; font-size:9px; background:transparent;"
        )

    # ---------- 位置 ----------

    def show_near(self, anchor: QWidget) -> None:
        self.adjustSize()
        geo = anchor.frameGeometry()
        x = geo.left() - self.width() - 14
        y = geo.bottom() - self.height() - 8
        screen = self.screen().availableGeometry() if self.screen() else geo
        x = max(screen.left() + 8, x)
        y = max(screen.top() + 8, y)
        self.move(QPoint(x, y))
        self.show()
        self.raise_()

    def follow(self, anchor: QWidget) -> None:
        if not self.isVisible():
            return
        geo = anchor.frameGeometry()
        self.move(QPoint(geo.left() - self.width() - 14, geo.bottom() - self.height() - 8))

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        p.setPen(QPen(BORDER, 1.2))
        p.setBrush(FILL)
        p.drawRoundedRect(rect, 18, 18)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(168, 200, 245, 26))
        p.drawRoundedRect(QRectF(rect.left(), rect.top(), rect.width(), 56), 18, 18)
        p.end()
