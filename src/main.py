"""星璃 Hoshiri · 桌宠入口。"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
from pet import PetWindow  # noqa: E402

_lock: QLockFile | None = None


def _acquire_lock() -> bool:
    """同一时间只允许一只桌宠；开机自启 + 手动双击不会出现两只。"""
    global _lock
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _lock = QLockFile(str(config.CONFIG_DIR / "hoshiri.lock"))
    _lock.setStaleLockTime(10_000)
    return _lock.tryLock(200)


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("HoshiriPet")
    app.setQuitOnLastWindowClosed(False)

    if not _acquire_lock():
        return 0

    window = PetWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
