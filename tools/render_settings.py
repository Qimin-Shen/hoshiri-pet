import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

import keystore
from ui.settings import SettingsDialog

app = QApplication([])

# 1) 凭据管理器读写测试
probe = "sk-roundtrip-test-000"
ok_write = keystore.set_key(probe)
back = keystore.get_key()
ok_read = back == probe
keystore.clear_key()
after_clear = keystore.get_key()
print(f"keyring write={ok_write} read_back={ok_read} cleared={after_clear == ''}")

# 2) 渲染设置窗口
dlg = SettingsDialog()
dlg.key_edit.setText("sk-********************************")
dlg.adjustSize()
pix = QPixmap(dlg.size())
pix.fill(QColor("#FFFFFF"))
dlg.render(pix)
out = Path(__file__).resolve().parent.parent / "docs" / "ui-settings.png"
pix.save(str(out))
print("saved", out, dlg.size().toTuple())
