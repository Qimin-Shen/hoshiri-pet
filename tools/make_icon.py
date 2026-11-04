"""从头像生成 Windows 图标（含多尺寸）。"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "out" / "avatar.png"
DST = ROOT / "assets" / "out" / "app.ico"

SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    img = Image.open(SRC).convert("RGBA")
    img.save(DST, format="ICO", sizes=SIZES)
    print(f"图标已生成：{DST}（{len(SIZES)} 个尺寸）")


if __name__ == "__main__":
    main()
