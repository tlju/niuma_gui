#!/usr/bin/env python3

import sys
import os
import traceback
import subprocess
import shutil
import platform
import tempfile

# 在导入任何应用模块之前，先验证关键配置（如 CRYPTO_KEY）
try:
    from core.config import settings
except ValueError as e:
    # CRYPTO_KEY 等配置校验失败时，无法使用 QMessageBox（Qt 尚未初始化），
    # 直接输出到控制台
    print(f"配置错误: {e}")
    input("按回车键退出...")
    sys.exit(1)
except Exception as e:
    print(f"加载配置失败: {e}")
    input("按回车键退出...")
    sys.exit(1)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox


def setup_linux_env():
    """
    设置Linux环境变量，包括运行时目录、Qt平台插件和输入法支持
    """
    if sys.platform != "linux":
        return
    
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "")
    if runtime_dir and os.path.exists(runtime_dir):
        try:
            stat_info = os.stat(runtime_dir)
            if stat_info.st_mode & 0o777 != 0o700:
                temp_runtime = os.path.join(tempfile.gettempdir(), f"runtime-{os.getuid()}")
                os.makedirs(temp_runtime, mode=0o700, exist_ok=True)
                os.environ["XDG_RUNTIME_DIR"] = temp_runtime
        except OSError:
            temp_runtime = os.path.join(tempfile.gettempdir(), f"runtime-{os.getuid()}")
            os.makedirs(temp_runtime, mode=0o700, exist_ok=True)
            os.environ["XDG_RUNTIME_DIR"] = temp_runtime
    
    if not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"
    
    app_root = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(app_root, "bin", "PyQt5", "Qt5", "plugins", "platforminputcontexts")
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
            except Exception as e:
                print(f"拷贝输入法插件失败: {e}")
    
    if not os.environ.get("QT_IM_MODULE"):
        os.environ["QT_IM_MODULE"] = "fcitx"


def show_error_dialog(title: str, message: str):
    """显示错误对话框，如无法创建 Qt 对话框则输出到控制台"""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        print(f"{title}: {message}")


def main():
    try:
        setup_linux_env()

        from core.logger import setup_logger
        setup_logger()

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv) 
        app.setApplicationName("运维辅助工具")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Niuma")

        from gui.icons import icons
        app.setWindowIcon(icons.app_icon())

        if sys.platform == "win32":
            import ctypes
            app_id = "Niuma.运维辅助工具.1.0.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

        from gui.style_manager import load_stylesheet, setup_app_fonts
        setup_app_fonts(app)
        load_stylesheet(app)

        from core.database import init_db
        init_db()

        from services.auth_service import AuthService
        auth_service = AuthService()

        from gui.login_dialog import LoginDialog
        login_dialog = LoginDialog(auth_service)
        if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
            sys.exit(0)

        from gui.main_window import MainWindow
        window = MainWindow(login_dialog.user_id, login_dialog.username)
        window.show()

        ret = app.exec()
        sys.exit(ret)
    except ValueError as e:
        error_msg = f"配置错误:\n{str(e)}"
        show_error_dialog("配置错误", error_msg)
        sys.exit(1)
    except Exception as e:
        error_msg = f"程序运行失败:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
        show_error_dialog("运行错误", error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
