"""测量实际重绘间隔，判断是「掉帧」还是「动画曲线不对」。"""

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import pet as pet_mod

app = QApplication([])
win = pet_mod.PetWindow()
win.show()

stamps: list[float] = []
original = pet_mod.PetWindow.paintEvent


def patched(self, event):
    stamps.append(time.perf_counter())
    original(self, event)


pet_mod.PetWindow.paintEvent = patched

QTimer.singleShot(3000, app.quit)
app.exec()

pet_mod.PetWindow.paintEvent = original

if len(stamps) < 5:
    print("帧数不足:", len(stamps))
    sys.exit()

gaps = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
print(f"总帧数: {len(stamps)}  时长: {(stamps[-1]-stamps[0]):.2f}s")
print(f"平均间隔: {statistics.mean(gaps):.1f} ms  -> {1000/statistics.mean(gaps):.1f} fps")
print(f"中位数:   {statistics.median(gaps):.1f} ms")
print(f"标准差:   {statistics.pstdev(gaps):.1f} ms")
print(f"最大间隔: {max(gaps):.1f} ms")
print(f"抖动 >5ms 的帧: {sum(1 for g in gaps if abs(g - statistics.mean(gaps)) > 5)} / {len(gaps)}")
