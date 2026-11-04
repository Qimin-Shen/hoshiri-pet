"""开机自启：写 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run。"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import winreg
except ImportError:  # 非 Windows 平台
    winreg = None  # type: ignore

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "HoshiriPet"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else exe
    main = Path(__file__).resolve().parent / "main.py"
    return f'"{runner}" "{main}"'


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
        return True
    except OSError:
        return False


def disable() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False
