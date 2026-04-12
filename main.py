#!/usr/bin/env python3

import sys
import os

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow
from gui.login_dialog import LoginDialog
from gui.style_manager import load_stylesheet, setup_app_fonts
from core.logger import setup_logger
from core.database import init_db, get_db_session
from services.auth_service import AuthService
from gui.icons import icons


def main():
    setup_logger()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    if sys.platform == "linux":
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("运维辅助工具")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Niuma")

    app.setWindowIcon(icons.app_icon())

    setup_app_fonts(app)
    load_stylesheet(app)

    init_db()
    db = get_db_session()
    auth_service = AuthService(db)

    login_dialog = LoginDialog(auth_service)
    if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
        db.close()
        sys.exit(0)

    window = MainWindow(login_dialog.user_id, login_dialog.username, db)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
