#!/usr/bin/env python3

import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt5.QtCore import Qt, QRectF


def create_app_icon():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    os.makedirs(icons_dir, exist_ok=True)

    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        color = QColor("#2c3e50")
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)

        screen_rect = QRectF(size * 0.1, size * 0.08, size * 0.8, size * 0.55)
        painter.drawRoundedRect(screen_rect, size * 0.08, size * 0.08)

        screen_inner = QRectF(size * 0.15, size * 0.13, size * 0.7, size * 0.45)
        painter.setBrush(QColor("#3498db"))
        painter.drawRoundedRect(screen_inner, size * 0.05, size * 0.05)

        painter.setBrush(color)
        stand_rect = QRectF(size * 0.35, size * 0.65, size * 0.3, size * 0.1)
        painter.drawRect(stand_rect)

        base_rect = QRectF(size * 0.2, size * 0.76, size * 0.6, size * 0.08)
        painter.drawRoundedRect(base_rect, size * 0.03, size * 0.03)

        painter.end()

        pixmap.save(os.path.join(icons_dir, f"app_{size}.png"))

    icon = QIcon()
    for size in sizes:
        pixmap = QPixmap(os.path.join(icons_dir, f"app_{size}.png"))
        icon.addPixmap(pixmap)

    icon_pixmap = icon.pixmap(256, 256)
    icon_pixmap.save(os.path.join(icons_dir, "app.ico"))
    icon_pixmap.save(os.path.join(icons_dir, "app.png"))

    print(f"图标文件已生成到 {icons_dir} 目录")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    create_app_icon()
