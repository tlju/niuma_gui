from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


def load_stylesheet(app: QApplication, style_name: str = None) -> None:
    styles_dir = Path(__file__).parent / "styles"
    
    if style_name:
        style_path = styles_dir / f"{style_name}.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    else:
        common_path = styles_dir / "common.qss"
        if common_path.exists():
            with open(common_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())


def load_combined_stylesheet(app: QApplication, style_names: list) -> None:
    styles_dir = Path(__file__).parent / "styles"
    combined_styles = ""
    
    for style_name in style_names:
        style_path = styles_dir / f"{style_name}.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                combined_styles += f.read() + "\n"
    
    if combined_styles:
        app.setStyleSheet(combined_styles)


def get_font() -> QFont:
    font = QFont()
    font.setFamilies(["Microsoft YaHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC", "sans-serif"])
    font.setPointSize(10)
    return font
