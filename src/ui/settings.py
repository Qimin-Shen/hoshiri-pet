"""Settings dialog for providers, proactive chat, persona and context privacy."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit, QScrollArea, QTimeEdit, QDoubleSpinBox,
    QVBoxLayout, QWidget,
)

import api_client
import config
import keystore

PROVIDERS = [("DeepSeek", "deepseek"), ("OpenAI (BoboWork)", "openai"), ("Anthropic (BoboWork)", "anthropic")]


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("星璃 · 设置")
        self.setMinimumSize(560, 720)
        self.resize(660, 820)
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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form_layout = QVBoxLayout(content)
        form_layout.setContentsMargins(0, 0, 6, 0)
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
        form.addRow("个人 API Key", self.key_edit)
        form_layout.addLayout(form)

        behavior = QFormLayout()
        behavior.setSpacing(8)
        self.chatter_enabled = QCheckBox("允许桌宠依据互动情况自适应地主动搭话")
        self.chatter_enabled.setChecked(bool(self.cfg.get("chatter", True)))
        behavior.addRow("主动对话", self.chatter_enabled)
        self.chatter_frequency = QDoubleSpinBox()
        self.chatter_frequency.setRange(0.01, 10.0)
        self.chatter_frequency.setDecimals(2)
        self.chatter_frequency.setSingleStep(0.05)
        self.chatter_frequency.setSuffix(" 次/分")
        self.chatter_frequency.setValue(float(self.cfg.get("chatter_frequency_per_minute", 0.02)))
        behavior.addRow("主动搭话频率", self.chatter_frequency)
        self.chatter_frequency_tip = QLabel("这是主动搭话的最高目标速率，实际可能因忙碌、勿扰或未回应退避而更低。0.1 次/分≈每 10 分钟一次；1 次/分≈每分钟一次。主动搭话为本地短句，不调用模型 API。关闭上方开关即可暂停。")
        self.chatter_frequency_tip.setWordWrap(True)
        self.chatter_frequency_tip.setStyleSheet("color:#7C99BC; font-size:11px;")
        behavior.addRow("频率说明", self.chatter_frequency_tip)
        self.quiet_enabled = QCheckBox("启用安静时段（跨午夜也有效）")
        self.quiet_enabled.setChecked(bool(self.cfg.get("quiet_hours_enabled", False)))
        behavior.addRow("勿扰", self.quiet_enabled)
        self.quiet_start = QTimeEdit()
        self.quiet_start.setDisplayFormat("HH:mm")
        self.quiet_start.setTime(QTime.fromString(self.cfg.get("quiet_start", "23:00"), "HH:mm"))
        self.quiet_end = QTimeEdit()
        self.quiet_end.setDisplayFormat("HH:mm")
        self.quiet_end.setTime(QTime.fromString(self.cfg.get("quiet_end", "08:00"), "HH:mm"))
        quiet_row = QHBoxLayout()
        quiet_row.addWidget(QLabel("从")); quiet_row.addWidget(self.quiet_start)
        quiet_row.addWidget(QLabel("到")); quiet_row.addWidget(self.quiet_end)
        behavior.addRow("安静时段", quiet_row)
        form_layout.addLayout(behavior)

        persona_title = QLabel("星璃 · 角色档案")
        persona_title.setStyleSheet("font-weight:600; font-size:14px; color:#49688F;")
        form_layout.addWidget(persona_title)
        self.persona_edit = QPlainTextEdit()
        self.persona_edit.setPlainText(self.cfg.get("persona_profile", config.DEFAULT_PERSONA))
        self.persona_edit.setMinimumHeight(270)
        self.persona_edit.setPlaceholderText("编辑完整的原创角色档案…")
        form_layout.addWidget(self.persona_edit)
        persona_tools = QHBoxLayout()
        self.persona_length = QLabel()
        self.persona_edit.textChanged.connect(self._update_persona_length)
        persona_tools.addWidget(self.persona_length)
        persona_tools.addStretch(1)
        btn_reset_persona = QPushButton("恢复星璃默认人设")
        btn_reset_persona.clicked.connect(lambda: self.persona_edit.setPlainText(config.DEFAULT_PERSONA))
        persona_tools.addWidget(btn_reset_persona)
        form_layout.addLayout(persona_tools)
        self.privacy_tip = QLabel("人设会随聊天发送给当前选择的模型服务商。长期记忆仅保存在本机；若启用并召回，也会随本轮请求发送给该服务商。记忆检索是关键词匹配，可能遗漏或误匹配；敏感信息过滤不保证绝对准确。屏幕、游戏状态和麦克风不会被读取。")
        self.privacy_tip.setWordWrap(True)
        self.privacy_tip.setStyleSheet("color:#8A6D4F; font-size:11px;")
        form_layout.addWidget(self.privacy_tip)

        self.memory_enabled = QCheckBox("启用本机记忆（保存前需我确认）")
        self.memory_enabled.setChecked(bool(self.cfg.get("memory_enabled", True)))
        form_layout.addWidget(self.memory_enabled)
        self.btn_memories = QPushButton("管理记忆…")
        self.btn_memories.clicked.connect(self._open_memories)
        self.btn_memories.setEnabled(self.memory_enabled.isChecked())
        self.memory_enabled.toggled.connect(self.btn_memories.setEnabled)
        form_layout.addWidget(self.btn_memories)

        self.use_local_time = QCheckBox("将本地时间与时区提供给对话模型")
        self.use_local_time.setChecked(bool(self.cfg.get("use_local_time", False)))
        form_layout.addWidget(self.use_local_time)
        self.use_weather = QCheckBox("启用天气上下文（手动设置城市；需联网）")
        self.use_weather.setChecked(bool(self.cfg.get("use_weather", False)))
        form_layout.addWidget(self.use_weather)
        self.weather_city = QLineEdit(self.cfg.get("weather_city", ""))
        self.weather_city.setPlaceholderText("例如：上海；不使用精确定位")
        form_layout.addWidget(self.weather_city)
        self.context_tip = QLabel("时间/天气仅在分别启用后才会随对话发送。天气使用 Open-Meteo；启用时将城市名发送给其地理编码服务并查询匹配城市天气。网络失败时忽略天气，上下文不阻塞普通聊天。")
        self.context_tip.setWordWrap(True)
        self.context_tip.setStyleSheet("color:#7C99BC; font-size:11px;")
        form_layout.addWidget(self.context_tip)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

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
        self._update_persona_length()

    def _update_persona_length(self) -> None:
        count = len(self.persona_edit.toPlainText())
        self.persona_length.setText(f"{count} / 12,000 字")
        self.persona_length.setStyleSheet("color:#C0392B;" if count > 12000 else "color:#7C99BC;")

    def _open_memories(self) -> None:
        from ui.memories import MemoriesDialog
        MemoriesDialog(self).exec()
        self.cfg = config.load()
        self.memory_enabled.setChecked(bool(self.cfg.get("memory_enabled", True)))

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
        return self.provider_box.currentData(), self.base_url_edit.text().strip(), self.key_edit.text().strip(), self.model_edit.text().strip()

    def _save(self) -> None:
        provider, base_url, key, model = self._current_values()
        if len(self.persona_edit.toPlainText()) > 12000:
            self.status.setText("角色档案超过 12,000 字，请精简后保存。")
            return
        self._key_drafts[provider] = key
        self.cfg.setdefault("provider_urls", {})[provider] = base_url
        self.cfg.setdefault("provider_models", {})[provider] = model
        self.cfg["provider"] = provider
        self.cfg["model"] = model
        self.cfg["chatter"] = self.chatter_enabled.isChecked()
        self.cfg["chatter_frequency_per_minute"] = self.chatter_frequency.value()
        self.cfg["quiet_hours_enabled"] = self.quiet_enabled.isChecked()
        self.cfg["quiet_start"] = self.quiet_start.time().toString("HH:mm")
        self.cfg["quiet_end"] = self.quiet_end.time().toString("HH:mm")
        self.cfg["persona_profile"] = self.persona_edit.toPlainText().strip()
        self.cfg["memory_enabled"] = self.memory_enabled.isChecked()
        self.cfg["use_local_time"] = self.use_local_time.isChecked()
        self.cfg["use_weather"] = self.use_weather.isChecked()
        self.cfg["weather_city"] = self.weather_city.text().strip()[:100]
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
        except Exception as exc:
            self.status.setText(f"失败：{exc}")
            self.status.setStyleSheet("font-size:11px; color:#C0392B;")
        finally:
            QApplication.restoreOverrideCursor()
