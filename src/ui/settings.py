"""Settings for provider, endpoint, model and credentials."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

import api_client
import config
import keystore

PROVIDERS = [("DeepSeek", "deepseek"), ("OpenAI (BoboWork)", "openai"), ("Anthropic (BoboWork)", "anthropic")]


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("星璃 · 设置")
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.cfg = config.load()
        self._key_drafts: dict[str, str] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)
        self.tip = QLabel()
        self.tip.setWordWrap(True)
        self.tip.setStyleSheet("color:#7C99BC; font-size:11px;")
        root.addWidget(self.tip)

        form = QFormLayout()
        form.setSpacing(8)
        self.provider_box = QComboBox()
        for label, provider in PROVIDERS:
            self.provider_box.addItem(label, provider)
        idx = self.provider_box.findData(self.cfg.get("provider", "deepseek"))
        self.provider_box.setCurrentIndex(max(0, idx))
        form.addRow("服务商", self.provider_box)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setFont(QFont("Consolas", 9))
        form.addRow("Base URL", self.base_url_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("填写服务商提供的模型 ID")
        self.model_edit.setFont(QFont("Consolas", 9))
        form.addRow("模型名称", self.model_edit)

        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("仅保存在 Windows 凭据管理器")
        self.key_edit.setFont(QFont("Consolas", 10))
        form.addRow("个人 API Key", self.key_edit)
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

        self.provider_box.currentIndexChanged.connect(self._provider_changed)
        self._load_provider(self.provider_box.currentData())

    def _provider_changed(self, _index: int) -> None:
        old = getattr(self, "_active_provider", None)
        if old:
            self._key_drafts[old] = self.key_edit.text().strip()
            self.cfg.setdefault("provider_urls", {})[old] = self.base_url_edit.text().strip()
            self.cfg.setdefault("provider_models", {})[old] = self.model_edit.text().strip()
        self._load_provider(self.provider_box.currentData())
        self.status.clear()

    def _load_provider(self, provider: str) -> None:
        self._active_provider = provider
        defaults = config.PROVIDER_DEFAULTS[provider]
        self.base_url_edit.setText(self.cfg.get("provider_urls", {}).get(provider, defaults["base_url"]))
        self.model_edit.setText(self.cfg.get("provider_models", {}).get(provider, defaults["model"]))
        self.key_edit.setText(self._key_drafts.get(provider, keystore.get_key(provider)))
        details = {
            "deepseek": "DeepSeek 直连：连接测试会查询 DeepSeek 余额。API Key 保存在 Windows 凭据管理器。",
            "openai": "OpenAI Chat Completions 协议。BoboWork Base URL 已预填；填写 BoboWork 提供的模型 ID。测试会发送一条极短请求，可能计入用量。",
            "anthropic": "Anthropic Messages 协议。BoboWork Base URL 已预填；填写 BoboWork 提供的模型 ID。测试会发送一条极短请求，可能计入用量。",
        }
        self.tip.setText(details[provider])

    def _current_values(self) -> tuple[str, str, str, str]:
        return (self.provider_box.currentData(), self.base_url_edit.text().strip(),
                self.key_edit.text().strip(), self.model_edit.text().strip())

    def _save(self) -> None:
        provider, base_url, key, model = self._current_values()
        self._key_drafts[provider] = key
        self.cfg.setdefault("provider_urls", {})[provider] = base_url
        self.cfg.setdefault("provider_models", {})[provider] = model
        self.cfg["provider"] = provider
        self.cfg["model"] = model  # legacy compatibility for older builds
        for name, draft in self._key_drafts.items():
            if draft and not keystore.set_key(draft, name):
                self.status.setText(f"写入 {name} 凭据失败")
                return
        config.save(self.cfg)
        self.accept()

    def _test(self) -> None:
        provider, base_url, key, model = self._current_values()
        if provider != "deepseek" and not model:
            self.status.setText("请填写服务商提供的模型 ID；我不会猜测网关已开通的模型。")
            return
        self.status.setText("连接中…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = api_client.test_connection(provider, base_url, key, model)
            self.status.setText(result)
            self.status.setStyleSheet("font-size:11px; color:#2B6FD6;")
        except Exception as exc:  # noqa: BLE001
            self.status.setText(f"失败：{exc}")
            self.status.setStyleSheet("font-size:11px; color:#C0392B;")
        finally:
            QApplication.restoreOverrideCursor()
