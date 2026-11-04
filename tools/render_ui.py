import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication
from ui.panel import Dashboard
from ui.bubble import SpeechBubble

app = QApplication([])

def shot(w, path, bg=None):
    from PySide6.QtGui import QPixmap
    w.adjustSize()
    pix = QPixmap(w.size())
    pix.fill(QColor(bg) if bg else Qt.GlobalColor.transparent)
    w.render(pix)
    pix.save(path)
    print("saved", path, w.size().toTuple())

d = Dashboard()
d.update_data(12.34, "CNY", 0.42, 1540, 84521,
              [(f"11-0{i}", v) for i, v in enumerate([3200,5800,2100,7600,4300,9100,2400], 1)],
              "更新于 17:52")
d.set_state("已连接 · 每分钟刷新")
shot(d, "docs/ui-dashboard.png", "#1B2340")

b = SpeechBubble()
b.set_text("晚上好呀～今天想聊点什么？我先看看你的余额哦。")
shot(b, "docs/ui-bubble.png", "#1B2340")


