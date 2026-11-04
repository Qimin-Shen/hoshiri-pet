"""桌宠主窗口：透明置顶、贴边停靠、对话与额度面板。"""

from __future__ import annotations

import math
import random
import threading
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

import config
import deepseek
import keystore
import store
import autostart
from particles import ParticleField
from effects import Effects, paint_glow
from layers import Character
from ui.bubble import SpeechBubble
from ui.chatbox import ChatInput
from ui.panel import Dashboard
from ui.settings import SettingsDialog

from paths import ASSETS

ACCENT = QColor("#A9C9F2")
GOLD = QColor("#F0D28A")
MAX_HISTORY = 10


class ChatSignals(QObject):
    chunk = Signal(str)
    done = Signal(dict)
    error = Signal(str)


class BalanceSignals(QObject):
    ok = Signal(dict)
    error = Signal(str)


class PetWindow(QWidget):
    MARGIN_X = 56
    MARGIN_TOP = 96
    MARGIN_BOTTOM = 8

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.cfg = config.load()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setWindowTitle("星璃 Hoshiri")

        self._char = Character(ASSETS / "hd")
        self._effects = Effects()

        self._t0 = time.time()
        self._drag_offset: QPoint | None = None
        self._drag_vx = 0.0
        self._drag_inertia = 0.0
        self._blink_until = 0.0
        self._next_blink = time.time() + 3.0
        self._busy = False
        self._stream = ""
        self._history: list[dict] = []
        self._chat_sig: ChatSignals | None = None
        self._balance_sig: BalanceSignals | None = None
        self._balance: dict | None = None

        self._particles = ParticleField(14)
        self._relayout()

        self.bubble = SpeechBubble()
        self.chatbox = ChatInput()
        self.chatbox.submitted.connect(self.send_message)
        self.dashboard = Dashboard()
        self.dashboard.refresh_requested.connect(lambda: self.refresh_balance(force=True))
        self.dashboard.settings_requested.connect(self.open_settings)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

        self._balance_timer = QTimer(self)
        self._balance_timer.timeout.connect(lambda: self.refresh_balance())
        self._balance_timer.start(60_000)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.bubble.hide)

        self._tray = self._build_tray()
        self._place_initial()
        self._prime_dashboard()
        QTimer.singleShot(1500, lambda: self.refresh_balance())
        QTimer.singleShot(2600, self._greet)

    def _greet(self) -> None:
        if not keystore.get_key():
            self.say("右键 → 设置，填上 DeepSeek 的 API Key，就能跟我聊天啦～", 12_000)
        else:
            self.say("我在呢～双击我就能聊天。", 6_000)

    # ---------- 布局 ----------

    def _scaled_size(self) -> tuple[int, int]:
        h = int(self.cfg["height"])
        cw, ch = self._char.size()
        w = int(cw * h / ch)
        return w, h

    def _relayout(self) -> None:
        w, h = self._scaled_size()
        self._content = (w, h)
        self.setFixedSize(w + self.MARGIN_X * 2, h + self.MARGIN_TOP + self.MARGIN_BOTTOM)
        self._particles.resize(self.width(), self.height())

    def _place_initial(self) -> None:
        pos = self.cfg.get("pos")
        if pos and len(pos) == 2:
            self.move(int(pos[0]), int(pos[1]))
        else:
            self.dock_bottom_right()

    def dock_bottom_right(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() + self.MARGIN_X // 2
        y = screen.bottom() - self.height() + 6
        self.move(x, y)

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._reposition_overlays()

    def _reposition_overlays(self) -> None:
        geo = self.frameGeometry()
        cx = geo.center().x()
        head_bottom = geo.top() + 96

        if self.chatbox.isVisible():
            self.chatbox.move(
                QPoint(cx - self.chatbox.width() // 2, head_bottom - self.chatbox.height() - 6)
            )
            bubble_bottom = self.chatbox.y() - 8
        else:
            bubble_bottom = head_bottom

        if self.bubble.isVisible():
            self.bubble.move(
                QPoint(cx - self.bubble.width() // 2, bubble_bottom - self.bubble.height())
            )
        self.dashboard.follow(self)

    # ---------- 绘制 ----------

    def _on_tick(self) -> None:
        now = time.time()
        if self.cfg["particles"]:
            self._particles.tick()
        self._effects.tick(0.033)

        # 眨眼调度
        if now >= self._next_blink:
            self._blink_until = now + random.uniform(0.09, 0.14)
            gap = random.uniform(2.4, 6.5)
            if random.random() < 0.18:      # 偶尔连眨两下
                self._next_blink = now + 0.35
            else:
                self._next_blink = now + gap

        # 拖拽惯性衰减
        self._drag_inertia *= 0.90
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        t = time.time() - self._t0
        bob = math.sin(t * 1.6) * 2.4
        breathe = 1.0 + 0.006 * math.sin(t * 1.15)
        tilt = 0.7 * math.sin(t * 0.85)

        w, h = self._content
        cx = self.width() / 2
        bottom = self.height() - self.MARGIN_BOTTOM + bob
        blink = time.time() < self._blink_until

        # 背后柔光：随呼吸脉动
        paint_glow(p, cx, bottom - h * 0.55, w * 0.60, math.sin(t * 1.15))

        p.save()
        p.translate(cx, bottom)
        p.rotate(tilt)
        p.scale(breathe, breathe)
        self._char.draw(p, QRectF(-w / 2, -h, w, h), t, blink, self._drag_inertia)
        p.restore()

        # 落地阴影
        shadow = QRectF(cx - w * 0.40, bottom - 14, w * 0.80, 20)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(6):
            p.setBrush(QColor(120, 170, 240, 20 - i * 3))
            p.drawEllipse(shadow.adjusted(i * 3, i * 1.5, -i * 3, -i * 1.5))

        if self.cfg["particles"]:
            self._particles.paint(p, ACCENT, GOLD)
        self._effects.paint(p)

        if self._busy:
            self._paint_thinking(p, cx, bottom - h - 18, t)
        p.end()

    def _paint_thinking(self, p: QPainter, cx: float, y: float, t: float) -> None:
        """思考中：头顶三个跳动的点。"""
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            phase = t * 4.2 - i * 0.55
            lift = max(0.0, math.sin(phase)) * 5
            alpha = 120 + int(100 * max(0.0, math.sin(phase)))
            p.setBrush(QColor(140, 185, 245, alpha))
            p.drawEllipse(QPointF(cx - 14 + i * 14, y - lift), 2.6, 2.6)

    # ---------- 对话 ----------

    def say(self, text: str, hold_ms: int = 6000) -> None:
        self.bubble.set_text(text)
        self._reposition_overlays()
        self._hide_timer.start(hold_ms)

    def open_chat(self) -> None:
        self.chatbox.open_at(self)
        self._reposition_overlays()

    def send_message(self, text: str) -> None:
        if self._busy:
            return
        key = keystore.get_key()
        if not key:
            self.say("还没绑定 API Key 哦～右键 → 设置")
            return

        self._busy = True
        self._stream = ""
        self._history.append({"role": "user", "content": text})
        self.bubble.set_text("…")
        self._reposition_overlays()
        self._hide_timer.stop()

        self._chat_sig = ChatSignals()
        self._chat_sig.chunk.connect(self._on_chunk)
        self._chat_sig.done.connect(self._on_chat_done)
        self._chat_sig.error.connect(self._on_chat_error)

        messages = self._history[-MAX_HISTORY:]
        model = self.cfg.get("model", deepseek.DEFAULT_MODEL)
        sig = self._chat_sig

        def worker() -> None:
            usage: dict = {}
            try:
                for piece, u in deepseek.stream_chat(key, messages, model):
                    if piece:
                        sig.chunk.emit(piece)
                    if u:
                        usage = u
                sig.done.emit(usage)
            except Exception as exc:  # noqa: BLE001
                sig.error.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_chunk(self, piece: str) -> None:
        self._stream += piece
        self.bubble.set_text(self._stream)
        self._reposition_overlays()

    def _on_chat_done(self, usage: dict) -> None:
        self._busy = False
        if self._stream:
            self._history.append({"role": "assistant", "content": self._stream})
            store.add_usage(
                self.cfg.get("model", deepseek.DEFAULT_MODEL),
                int(usage.get("prompt_tokens", 0) or 0),
                int(usage.get("completion_tokens", 0) or 0),
            )
        self._reposition_overlays()
        self._hide_timer.start(25_000)
        self._refresh_dashboard_values()

    def _on_chat_error(self, message: str) -> None:
        self._busy = False
        self.bubble.set_text(f"出错了：{message}")
        self._reposition_overlays()
        self._hide_timer.start(8000)

    # ---------- 额度 ----------

    def _prime_dashboard(self) -> None:
        last = store.last_balance()
        self._refresh_dashboard_values(last[0] if last else None, last[1][11:16] if last else "")

    def refresh_balance(self, force: bool = False) -> None:
        key = keystore.get_key()
        if not key:
            self.dashboard.set_state("未绑定 API Key · 右键 → 设置")
            if force:
                self.open_settings()
            return

        self._balance_sig = BalanceSignals()
        self._balance_sig.ok.connect(self._on_balance_ok)
        self._balance_sig.error.connect(self._on_balance_error)
        sig = self._balance_sig

        def worker() -> None:
            try:
                sig.ok.emit(deepseek.balance(key))
            except Exception as exc:  # noqa: BLE001
                sig.error.emit(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_balance_ok(self, info: dict) -> None:
        self._balance = info
        store.add_balance(info["total"], info["currency"])
        self.dashboard.set_state("已连接 · 每分钟刷新")
        self._refresh_dashboard_values(info["total"], datetime.now().strftime("%H:%M"))

    def _on_balance_error(self, message: str) -> None:
        self.dashboard.set_state(f"查询失败：{message}")

    def _refresh_dashboard_values(self, balance: float | None = None, updated: str = "") -> None:
        if balance is None:
            last = store.last_balance()
            balance = last[0] if last else None
            updated = updated or (last[1][11:16] if last else "")

        currency = (self._balance or {}).get("currency", "CNY")
        self.dashboard.update_data(
            balance=balance,
            currency=currency,
            today_cost=store.today_spend(),
            today_tokens=store.today_tokens(),
            total_tokens=store.total_tokens(),
            history=store.history(7),
            updated_at=f"更新于 {updated}" if updated else "尚无数据",
        )

    # ---------- 窗口行为 ----------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            self._effects.burst(pos.x(), pos.y())
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            dx = new_pos.x() - self.x()
            self._drag_inertia = max(-20.0, min(20.0, self._drag_inertia + dx * 0.5))
            self._effects.trail(event.position().x(), event.position().y(), dx)
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None:
            self._drag_offset = None
            self.cfg["pos"] = [self.x(), self.y()]
            config.save(self.cfg)
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.open_chat()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        menu = self.build_menu()
        menu.exec(event.globalPos())

    def build_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setFont(QFont("Microsoft YaHei UI", 9))

        act_chat = QAction("聊聊天", menu)
        act_chat.triggered.connect(self.open_chat)
        menu.addAction(act_chat)

        act_panel = QAction("额度面板", menu)
        act_panel.triggered.connect(self.toggle_dashboard)
        menu.addAction(act_panel)

        act_settings = QAction("设置…", menu)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()

        act_dock = QAction("停靠右下角", menu)
        act_dock.triggered.connect(self._reset_position)
        menu.addAction(act_dock)

        act_particles = QAction("星屑特效", menu)
        act_particles.setCheckable(True)
        act_particles.setChecked(bool(self.cfg["particles"]))
        act_particles.toggled.connect(self._toggle_particles)
        menu.addAction(act_particles)

        size_menu = menu.addMenu("大小")
        for label, h in (("小", 220), ("中", 300), ("大", 400)):
            a = QAction(label, size_menu)
            a.setCheckable(True)
            a.setChecked(self.cfg["height"] == h)
            a.triggered.connect(lambda _=False, hh=h: self._set_height(hh))
            size_menu.addAction(a)

        act_auto = QAction("开机自启", menu)
        act_auto.setCheckable(True)
        act_auto.setChecked(autostart.is_enabled())
        act_auto.toggled.connect(self._toggle_autostart)
        menu.addAction(act_auto)

        menu.addSeparator()
        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_quit)
        return menu

    def toggle_dashboard(self) -> None:
        if self.dashboard.isVisible():
            self.dashboard.hide()
        else:
            self._refresh_dashboard_values()
            self.dashboard.show_near(self)
            self.refresh_balance()

    def open_settings(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.say("设置已保存～")
            self.refresh_balance()

    def _reset_position(self) -> None:
        self.dock_bottom_right()
        self.cfg["pos"] = [self.x(), self.y()]
        config.save(self.cfg)
        self._reposition_overlays()

    def _toggle_particles(self, on: bool) -> None:
        self.cfg["particles"] = bool(on)
        config.save(self.cfg)

    def _toggle_autostart(self, on: bool) -> None:
        ok = autostart.enable() if on else autostart.disable()
        if ok:
            self.say("已开启开机自启～" if on else "已关闭开机自启～", 4000)
        else:
            self.say("设置开机自启失败，可能被安全软件拦了", 6000)

    def _set_height(self, h: int) -> None:
        self.cfg["height"] = h
        self._relayout()
        self._reset_position()

    # ---------- 托盘 ----------

    def _build_tray(self) -> QSystemTrayIcon:
        icon_path = ASSETS / "avatar.png"
        tray = QSystemTrayIcon(QIcon(str(icon_path)) if icon_path.exists() else QIcon(), self)
        tray.setToolTip("星璃 Hoshiri")

        menu = QMenu()
        menu.setFont(QFont("Microsoft YaHei UI", 9))
        for label, slot in (
            ("显示 / 隐藏", self._toggle_visible),
            ("额度面板", self.toggle_dashboard),
            ("设置…", self.open_settings),
            ("退出", QApplication.quit),
        ):
            act = QAction(label, menu)
            act.triggered.connect(slot)
            menu.addAction(act)

        tray.setContextMenu(menu)
        tray.activated.connect(
            lambda reason: self._toggle_visible()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        tray.show()
        return tray

    def _toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
            self.bubble.hide()
            self.chatbox.hide()
            self.dashboard.hide()
        else:
            self.show()
            self.raise_()



