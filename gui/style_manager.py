import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import QSysInfo


def _get_resource_path(relative_path: str) -> Path:
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
        return base_path / relative_path
    else:
        base_path = Path(__file__).parent.parent
        return base_path / relative_path


def _detect_platform_font() -> list:
    font_list = []
    if sys.platform == "win32":
        font_list = [
            "Microsoft YaHei", "Segoe UI", "SimHei",
            "PingFang SC", "Noto Sans CJK SC", "sans-serif"
        ]
    elif sys.platform == "darwin":
        font_list = [
            "PingFang SC", "Heiti SC", "STHeiti",
            "Noto Sans CJK SC", "Microsoft YaHei", "sans-serif"
        ]
    else:
        font_list = [
            "Noto Sans CJK SC", "WenQuanYi Micro Hei",
            "WenQuanYi Zen Hei", "Droid Sans Fallback",
            "Microsoft YaHei", "sans-serif"
        ]

    available = QFontDatabase().families()
    for font_name in font_list:
        if font_name in available or font_name == "sans-serif":
            return [font_name]

    return ["sans-serif"]


def _detect_font_size() -> int:
    if sys.platform == "win32":
        try:
            import ctypes
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 90)
            ctypes.windll.user32.ReleaseDC(0, hdc)
            if dpi > 120:
                return 11
        except Exception:
            pass
        return 10
    elif sys.platform == "darwin":
        return 13
    else:
        return 10


def load_stylesheet(app: QApplication, style_name: str = None) -> None:
    styles_dir = _get_resource_path("gui/styles")

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
    styles_dir = _get_resource_path("gui/styles")
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
    preferred_fonts = _detect_platform_font()
    font.setFamilies(preferred_fonts)
    font.setPointSize(_detect_font_size())
    font.setStyleHint(QFont.SansSerif)
    font.setWeight(QFont.Normal)
    return font


def setup_app_fonts(app: QApplication) -> None:
    font = get_font()
    app.setFont(font)
