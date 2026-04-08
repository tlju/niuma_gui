#!/usr/bin/env python3
"""
牛马运维辅助系统 - GUI 版本
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow
from core.logger import setup_logger
from gui.icons import icons

def main():
    # 初始化日志系统
    setup_logger()

    # 启用高 DPI 缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Niuma 堡垒机")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Niuma")

    # 设置应用图标
    app.setWindowIcon(icons.app_icon())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
