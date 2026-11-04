import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
from PySide6.QtWidgets import QApplication
from pet import PetWindow
import store

app = QApplication([])
w = PetWindow()

# 菜单
names = [a.text() for a in w.build_menu().actions()]
print("menu:", names)

# 气泡
w.bubble.set_text("晚上好呀～今天想聊点什么？我先看看你的余额哦。")
w._reposition_overlays()
print("bubble size:", w.bubble.size().toTuple())

# 输入框
w.chatbox.open_at(w)
print("chatbox pos:", w.chatbox.pos().toTuple())

# 仪表盘（假数据）
store.add_usage("deepseek-chat", 1200, 340)
store.add_balance(12.34, "CNY")
w.dashboard.update_data(12.34, "CNY", 0.42, 1540, 84521,
                        [(f"2026-11-0{i}", i*900) for i in range(1,8)], "更新于 17:52")
w.dashboard.show_near(w)
print("dashboard size:", w.dashboard.size().toTuple(), "pos:", w.dashboard.pos().toTuple())

print("OK")
