#!/usr/bin/env python3

import sys
import os
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow
from gui.login_dialog import LoginDialog
from gui.style_manager import load_stylesheet, setup_app_fonts
from core.logger import setup_logger
from core.database import init_db, get_db_session
from services.auth_service import AuthService
from gui.icons import icons


def show_error_dialog(title: str, message: str):
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        print(f"{title}: {message}")


def main():
    try:
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

        if sys.platform == "win32":
            import ctypes
            app_id = "Niuma.运维辅助工具.1.0.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

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
    except Exception as e:
        error_msg = f"程序启动失败:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
        show_error_dialog("启动错误", error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
