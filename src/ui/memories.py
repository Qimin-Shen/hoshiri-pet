"""User-controlled memory management and explicit candidate review dialogs."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QMessageBox, QPushButton, QLineEdit, QVBoxLayout,
)

import memory
import config


class MemoriesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("星璃 · 记忆管理")
        self.resize(560, 500)
        layout = QVBoxLayout(self)
        self.notice = QLabel("记忆仅存于本机。被本轮对话召回的条目会随请求发送给当前模型服务商。")
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索记忆…")
        self.search.textChanged.connect(self.refresh)
        search_row.addWidget(self.search)
        layout.addLayout(search_row)
        self.items = QListWidget()
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.items, 1)
        self.enabled = QPushButton("暂停记忆" if config.load().get("memory_enabled", True) else "恢复记忆")
        self.enabled.setCheckable(True)
        self.enabled.setChecked(bool(config.load().get("memory_enabled", True)))
        self.enabled.toggled.connect(self.toggle_memory)
        layout.addWidget(self.enabled)
        buttons = QHBoxLayout()
        for label, slot in (("新增", self.add_memory), ("编辑", self.edit_memory), ("删除", self.delete_memory), ("清空全部", self.clear_memories)):
            button = QPushButton(label)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        close = QPushButton("关闭")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.refresh()

    def toggle_memory(self, enabled: bool) -> None:
        cfg = config.load()
        cfg["memory_enabled"] = bool(enabled)
        config.save(cfg)
        self.enabled.setText("暂停记忆" if enabled else "恢复记忆")

    def refresh(self, *_args) -> None:
        self.items.clear()
        for row in memory.list_memories(self.search.text()):
            self.items.addItem(f"#{row['id']} · {row['content']}")

    def _selected_id(self) -> int | None:
        item = self.items.currentItem()
        if not item:
            return None
        try:
            return int(item.text().split("·", 1)[0].strip().lstrip("#"))
        except ValueError:
            return None

    def add_memory(self) -> None:
        text, ok = QInputDialog.getMultiLineText(self, "新增记忆", "只写希望星璃以后记住的普通偏好或事实：")
        if ok and text.strip():
            try:
                memory.add(text)
            except ValueError as exc:
                QMessageBox.warning(self, "未保存", str(exc))
            self.refresh()

    def edit_memory(self) -> None:
        memory_id = self._selected_id()
        if memory_id is None:
            return
        row = next((m for m in memory.list_memories() if m["id"] == memory_id), None)
        if not row:
            return
        text, ok = QInputDialog.getMultiLineText(self, "编辑记忆", "记忆内容：", row["content"])
        if ok:
            try:
                memory.update(memory_id, text)
            except ValueError as exc:
                QMessageBox.warning(self, "未保存", str(exc))
            self.refresh()

    def delete_memory(self) -> None:
        memory_id = self._selected_id()
        if memory_id is None:
            return
        answer = QMessageBox.question(self, "确认删除", "删除选中的记忆？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            memory.delete(memory_id)
            self.refresh()

    def clear_memories(self) -> None:
        if not memory.list_memories():
            return
        answer = QMessageBox.question(self, "确认清空", "永久删除本机保存的全部记忆？此操作不可撤销。", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            memory.clear_all()
            self.refresh()


class MemoryCandidateDialog(QDialog):
    def __init__(self, candidate: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("要保存为记忆吗？")
        self.candidate = candidate
        layout = QVBoxLayout(self)
        label = QLabel("星璃发现一条可能有帮助的信息。只有你确认后才会存入本机记忆；以后被对话召回时会发送给当前模型服务商。")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.content = QLineEdit(candidate)
        layout.addWidget(self.content)
        row = QHBoxLayout()
        self.accept_button = QPushButton("保存")
        self.accept_button.clicked.connect(self.accept)
        row.addWidget(self.accept_button)
        self.ignore_button = QPushButton("忽略")
        self.ignore_button.clicked.connect(self.reject)
        row.addWidget(self.ignore_button)
        layout.addLayout(row)
