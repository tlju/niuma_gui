#!/usr/bin/env python3

import sys
import os
import traceback

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox
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

        if sys.platform == "linux":
            os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
            os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
            
            if "QT_IM_MODULE" not in os.environ:
                im_module = os.environ.get("GTK_IM_MODULE", "") or os.environ.get("XMODIFIERS", "")
                if "fcitx" in im_module.lower():
                    os.environ["QT_IM_MODULE"] = "fcitx"
                elif "ibus" in im_module.lower():
                    os.environ["QT_IM_MODULE"] = "ibus"
                elif os.path.exists("/usr/bin/fcitx") or os.path.exists("/usr/bin/fcitx5") or \
                     os.path.exists("/usr/local/bin/fcitx") or os.path.exists("/usr/local/bin/fcitx5") or \
                     os.path.exists("/usr/bin/sogou-qimpanel") or \
                     os.path.exists("/opt/apps/com.sogou.sogoupinyin-uos"):
                    os.environ["QT_IM_MODULE"] = "fcitx"
                elif os.path.exists("/usr/bin/ibus-daemon") or os.path.exists("/usr/local/bin/ibus-daemon"):
                    os.environ["QT_IM_MODULE"] = "ibus"
            
            sogou_plugin_paths = [
                "/usr/lib/x86_64-linux-gnu/qt5/plugins/platforminputcontexts",
                "/usr/lib/aarch64-linux-gnu/qt5/plugins/platforminputcontexts",
                "/usr/lib/arm-linux-gnueabihf/qt5/plugins/platforminputcontexts",
                "/opt/sogou-pinyin/files/lib/qt5/plugins/platforminputcontexts",
                "/opt/apps/com.sogou.sogou-pinyin/files/lib/qt5/plugins/platforminputcontexts",
                "/opt/apps/com.sogou.sogoupinyin-uos/files/lib/qt5/plugins/platforminputcontexts",
                "/usr/lib/qt5/plugins/platforminputcontexts",
            ]
            existing_plugin_paths = [p for p in sogou_plugin_paths if os.path.exists(p)]
            if existing_plugin_paths:
                current_path = os.environ.get("QT_PLUGIN_PATH", "")
                new_paths = ":".join(existing_plugin_paths)
                if current_path:
                    os.environ["QT_PLUGIN_PATH"] = f"{new_paths}:{current_path}"
                else:
                    os.environ["QT_PLUGIN_PATH"] = new_paths

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
