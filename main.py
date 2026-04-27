#!/usr/bin/env python3

import sys
import os
import traceback
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox


def setup_input_method():
    """
    设置Qt输入法环境变量，支持Linux下的中文输入
    支持Fcitx、IBus、搜狗输入法等
    """
    if sys.platform != "linux":
        return
    
    current_im = os.environ.get("QT_IM_MODULE", "")
    if current_im:
        return
    
    sogou_paths = [
        "/opt/apps/com.sogou.sogoupinyin-uos",
        "/opt/sogoupinyin",
        "/usr/share/fcitx-sogoupinyin",
    ]
    has_sogou = any(os.path.exists(p) for p in sogou_paths)
    
    if has_sogou:
        os.environ["QT_IM_MODULE"] = "fcitx"
        os.environ["GTK_IM_MODULE"] = "fcitx"
        os.environ["XMODIFIERS"] = "@im=fcitx"
        return
    
    try:
        result = subprocess.run(
            ["pgrep", "-x", "fcitx"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            os.environ["QT_IM_MODULE"] = "fcitx"
            os.environ["GTK_IM_MODULE"] = "fcitx"
            os.environ["XMODIFIERS"] = "@im=fcitx"
            return
    except Exception:
        pass
    
    try:
        result = subprocess.run(
            ["pgrep", "-x", "ibus-daemon"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            os.environ["QT_IM_MODULE"] = "ibus"
            os.environ["GTK_IM_MODULE"] = "ibus"
            os.environ["XMODIFIERS"] = "@im=ibus"
            return
    except Exception:
        pass
    
    fcitx5_paths = [
        "/usr/bin/fcitx5",
        "/usr/bin/fcitx5-remote",
    ]
    if any(os.path.exists(p) for p in fcitx5_paths):
        os.environ["QT_IM_MODULE"] = "fcitx"
        os.environ["GTK_IM_MODULE"] = "fcitx"
        os.environ["XMODIFIERS"] = "@im=fcitx"


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
        setup_input_method()
        setup_logger()

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

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
