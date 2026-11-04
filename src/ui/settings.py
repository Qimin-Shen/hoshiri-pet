"""设置：API Key、模型。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config
import deepseek
import keystore


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("星璃 · 设置")
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.cfg = config.load()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)

        tip = QLabel(
            "API Key 保存在 Windows 凭据管理器里，不会写进任何配置文件。\n"
            "在 https://platform.deepseek.com/api_keys 创建。"
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#7C99BC; font-size:11px;")
        root.addWidget(tip)

        form = QFormLayout()
        form.setSpacing(8)

        self.key_edit = QLineEdit(keystore.get_key())
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-...")
        self.key_edit.setFont(QFont("Consolas", 10))
        form.addRow("API Key", self.key_edit)

        self.model_box = QComboBox()
        self.model_box.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.model_box.setCurrentText(self.cfg.get("model", deepseek.DEFAULT_MODEL))
        form.addRow("模型", self.model_box)

        root.addLayout(form)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("font-size:11px; color:#7C99BC;")
        root.addWidget(self.status)

        row = QHBoxLayout()
        btn_test = QPushButton("测试连接")
        btn_test.clicked.connect(self._test)
        row.addWidget(btn_test)
        row.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_cancel)
        btn_save = QPushButton("保存")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        row.addWidget(btn_save)
        root.addLayout(row)

    def _save(self) -> None:
        key = self.key_edit.text().strip()
        if key:
            if not keystore.set_key(key):
                self.status.setText("写入凭据管理器失败")
                return
        self.cfg["model"] = self.model_box.currentText()
        config.save(self.cfg)
        self.accept()

    def _test(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            self.status.setText("先填 API Key")
            return
        self.status.setText("连接中…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            info = deepseek.balance(key)
            self.status.setText(
                f"连接成功 · 余额 {info['currency']} {info['total']:.2f} · "
                f"可用={info['is_available']}"
            )
            self.status.setStyleSheet("font-size:11px; color:#2B6FD6;")
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"失败：{exc}")
            self.status.setStyleSheet("font-size:11px; color:#C0392B;")
        finally:
            QApplication.restoreOverrideCursor()


