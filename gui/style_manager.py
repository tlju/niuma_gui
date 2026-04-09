from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


def load_stylesheet(app: QApplication) -> None:
    style_path = Path(__file__).parent / "styles.qss"
    if style_path.exists():
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def get_font() -> QFont:
    font = QFont()
    font.setFamilies(["Microsoft YaHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "sans-serif"])
    font.setPointSize(10)
    return font
