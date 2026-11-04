"""额度仪表盘：余额 / 今日 / 累计 + 近 7 天柱状图。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

CARD_W = 286
INK = "#2B4C8C"
MUTED = "#7C99BC"
ACCENT = "#2B6FD6"
GOLD = "#D9AE55"
BORDER = QColor(169, 201, 242, 235)
FILL = QColor(255, 255, 255, 246)


class BarChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.values: list[tuple[str, int]] = []
        self.setFixedHeight(46)

    def set_values(self, values: list[tuple[str, int]]) -> None:
        self.values = values[-7:]
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

        n = len(self.values)
        gap = 6
        bar_w = max(8.0, (self.width() - gap * (n - 1)) / n)
        peak = max((v for _, v in self.values), default=0) or 1
        base = self.height() - 12

        for i, (_day, v) in enumerate(self.values):
            h = 2 + (base - 6) * (v / peak)
            x = i * (bar_w + gap)
            color = QColor(ACCENT) if v else QColor(210, 226, 245)
            color.setAlpha(220)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(int(x), int(base - h), int(bar_w), int(h), 3, 3)

        p.setPen(QColor(MUTED))
        p.setFont(QFont("Microsoft YaHei UI", 7))
        p.drawText(self.rect().adjusted(0, 0, 0, -2), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, "近 7 天")
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
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(6)

        title = QLabel("星璃 · 额度")
        title.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Medium))
        title.setStyleSheet(f"color:{MUTED}; background:transparent;")
        root.addWidget(title)

        self.balance = QLabel("--")
        self.balance.setFont(QFont("Microsoft YaHei UI", 26, QFont.Weight.DemiBold))
        self.balance.setStyleSheet(f"color:{INK}; background:transparent;")
        root.addWidget(self.balance)

        self.state = QLabel("未绑定 API Key")
        self.state.setFont(QFont("Microsoft YaHei UI", 8))
        self.state.setStyleSheet(f"color:{MUTED}; background:transparent;")
        root.addWidget(self.state)

        root.addSpacing(4)
        self.today_cost = self._stat_row(root, "今日花费")
        self.today_tokens = self._stat_row(root, "今日 tokens")
        self.total_tokens = self._stat_row(root, "累计 tokens")

        root.addSpacing(6)
        self.chart = BarChart(self)
        root.addWidget(self.chart)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)
        self.updated = QLabel("")
        self.updated.setFont(QFont("Microsoft YaHei UI", 8))
        self.updated.setStyleSheet(f"color:{MUTED}; background:transparent;")
        bottom.addWidget(self.updated)
        bottom.addStretch(1)

        btn_style = (
            "QPushButton{background:transparent;border:none;color:%s;"
            "font-size:11px;padding:2px 4px;}"
            "QPushButton:hover{color:%s;}"
        ) % (ACCENT, GOLD)

        btn_refresh = QPushButton("刷新")
        btn_refresh.setStyleSheet(btn_style)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh_requested)
        bottom.addWidget(btn_refresh)

        btn_settings = QPushButton("设置")
        btn_settings.setStyleSheet(btn_style)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.clicked.connect(self.settings_requested)
        bottom.addWidget(btn_settings)

        root.addLayout(bottom)

        self.hide()

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
    ) -> None:
        if balance is None:
            self.balance.setText("--")
        else:
            symbol = "¥" if currency.upper() in ("CNY", "RMB") else "$"
            self.balance.setText(f"{symbol}{balance:,.2f}")
        self.today_cost.setText(f"¥{today_cost:.2f}")
        self.today_tokens.setText(f"{today_tokens:,}")
        self.total_tokens.setText(f"{total_tokens:,}")
        self.chart.set_values(history)
        self.updated.setText(updated_at)

    def set_state(self, text: str) -> None:
        self.state.setText(text)

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
        p.setPen(QPen(BORDER, 1.2))
        p.setBrush(FILL)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
        p.end()

