#!/usr/bin/env python3

import sys
import os
import traceback
import subprocess
import shutil
import platform

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox


def setup_input_method():
    """
    设置Qt输入法环境变量，支持Linux下的中文输入
    检测并拷贝fcitx输入法插件
    """
    if sys.platform != "linux":
        return
    
    current_im = os.environ.get("QT_IM_MODULE", "")
    if current_im:
        return
    
    target_dir = os.path.join("bin", "PyQt5", "Qt5", "plugins", "platforminputcontexts")
    target_plugin = os.path.join(target_dir, "libfcitxplatforminputcontextplugin.so")
    
    if not os.path.exists(target_plugin):
        os.makedirs(target_dir, exist_ok=True)
        
        machine = platform.machine()
        if machine == "aarch64":
            source_plugin = "/usr/lib/aarch64-linux-gnu/qt5/plugins/platforminputcontexts/libfcitxplatforminputcontextplugin.so"
        else:
            source_plugin = "/usr/lib/x86_64-linux-gnu/qt5/plugins/platforminputcontexts/libfcitxplatforminputcontextplugin.so"
        
        if os.path.exists(source_plugin):
            try:
                shutil.copy(source_plugin, target_plugin)
            except Exception:
                pass
    
    os.environ["QT_IM_MODULE"] = "fcitx"


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
