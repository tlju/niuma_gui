from __future__ import annotations

from PyQt5.QtCore import QThread, pyqtSignal
from typing import Callable, Any, Tuple, List, Optional
import traceback
from core.database import get_thread_db
from core.secure_string import SecureString
from core.config import settings


class BaseWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            result = self.execute()
            self.finished.emit(result)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

    def execute(self) -> Any:
        raise NotImplementedError


class DatabaseWorker(BaseWorker):
    def __init__(self, db_func: Callable, *args, **kwargs):
        super().__init__()
        self.db_func = db_func
        self.args = args
        self.kwargs = kwargs

    def execute(self) -> Any:
        with get_thread_db() as db:
            return self.db_func(db, *self.args, **self.kwargs)


class GenericWorker(BaseWorker):
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def execute(self) -> Any:
        return self.func(*self.args, **self.kwargs)


class DeleteWorker(BaseWorker):
    def __init__(self, delete_func: Callable, *args, **kwargs):
        super().__init__()
        self.delete_func = delete_func
        self.args = args
        self.kwargs = kwargs

    def execute(self) -> Any:
        with get_thread_db() as db:
            return self.delete_func(db, *self.args, **self.kwargs)


class BastionConnectionWorker(QThread):
    status_changed = pyqtSignal(str, str)
    connection_failed = pyqtSignal(str)
    connection_success = pyqtSignal()
    auth_required = pyqtSignal(dict)
    retry_attempt = pyqtSignal(int, int, str)

    def __init__(self, bastion_service, max_retries: int = None,
                 retry_interval: int = None, parent=None):
        super().__init__(parent)
        self.bastion_service = bastion_service
        self.max_retries = max_retries or settings.BASTION_MAX_RETRIES
        self.retry_interval = retry_interval or settings.BASTION_RETRY_INTERVAL
        self._is_cancelled = False
        self.connection = None

    def run(self):
        from services.bastion_service import ConnectionStatus
        try:
            self.status_changed.emit(ConnectionStatus.CONNECTING.value, "正在连接堡垒机...")
            logger_msg = "BastionConnectionWorker: 开始连接堡垒机"

            def on_status_change(status: ConnectionStatus, message: str):
                if not self._is_cancelled:
                    self.status_changed.emit(status.value, message)

            def on_retry(attempt: int, error: str):
                if not self._is_cancelled:
                    self.retry_attempt.emit(attempt, self.max_retries, error)

            self.connection = self.bastion_service.connect_with_retry(
                connection_id="default",
                max_retries=self.max_retries,
                retry_interval=self.retry_interval,
                on_status_change=on_status_change,
                on_retry=on_retry
            )

            if self._is_cancelled:
                self.bastion_service.disconnect("default")
                return

            self.status_changed.emit(ConnectionStatus.CONNECTED.value, "已连接，检测认证方式...")

            auth_info = self.bastion_service.detect_auth_prompt("default")

            if auth_info.get("needs_password") or auth_info.get("needs_otp") or auth_info.get("needs_menu"):
                self.auth_required.emit(auth_info)
            else:
                self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value, "认证成功")
                self.bastion_service.start_keepalive("default")
                self.connection_success.emit()

        except Exception as e:
            if not self._is_cancelled:
                from services.bastion_service import ConnectionStatus
                self.status_changed.emit(ConnectionStatus.FAILED.value, str(e))
                self.connection_failed.emit(str(e))

    def cancel(self):
        self._is_cancelled = True


class BastionAuthWorker(QThread):
    status_changed = pyqtSignal(str, str)
    auth_success = pyqtSignal()
    auth_failed = pyqtSignal(str)
    otp_retry_required = pyqtSignal()
    server_list_available = pyqtSignal(list, str)

    def __init__(self, bastion_service, otp_code: str = None,
                 menu_selection: str = None, parent=None):
        super().__init__(parent)
        self.bastion_service = bastion_service
        self.otp_code = otp_code
        self.menu_selection = menu_selection

    def run(self):
        from services.bastion_service import ConnectionStatus
        try:
            self.status_changed.emit(ConnectionStatus.AUTHENTICATING.value, "正在进行二次认证...")

            result = self.bastion_service.authenticate(
                connection_id="default",
                auth_type="otp",
                otp_code=self.otp_code,
                menu_selection=self.menu_selection
            )

            if result.get("has_server_list"):
                server_list = result.get("server_list", [])
                raw_output = result.get("output", "")
                self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value, "认证成功，请选择目标服务器")
                self.server_list_available.emit(server_list, raw_output)
            else:
                self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value, "认证成功")
                self.bastion_service.start_keepalive("default")
                self.auth_success.emit()

        except Exception as e:
            if str(e) == "OTP_RETRY":
                self.otp_retry_required.emit()
            else:
                from services.bastion_service import ConnectionStatus
                self.status_changed.emit(ConnectionStatus.FAILED.value, str(e))
                self.auth_failed.emit(str(e))


class AssetConnectionWorker(QThread):
    status_changed = pyqtSignal(str, str)
    connection_success = pyqtSignal(str)
    connection_failed = pyqtSignal(str)

    def __init__(self, bastion_service, target_ip: str, asset_username: str,
                 asset_password: str, parent=None):
        super().__init__(parent)
        self.bastion_service = bastion_service
        self.target_ip = target_ip
        self.asset_username = asset_username
        self._secure_password = SecureString(asset_password)

    def run(self):
        from services.bastion_service import ConnectionStatus
        try:
            self.status_changed.emit(ConnectionStatus.AUTHENTICATING.value,
                                     f"正在连接资产 {self.target_ip}...")

            result = self.bastion_service.connect_to_asset(
                connection_id="default",
                target_ip=self.target_ip,
                asset_username=self.asset_username,
                asset_password=self._secure_password.consume(),
                timeout=60
            )

            if result.get("success"):
                self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value,
                                         f"已连接: {self.target_ip}")
                self.connection_success.emit(self.target_ip)
            else:
                error = result.get("error", "未知错误")
                self.status_changed.emit(ConnectionStatus.FAILED.value, error)
                self.connection_failed.emit(error)

        except Exception as e:
            from services.bastion_service import ConnectionStatus
            self.status_changed.emit(ConnectionStatus.FAILED.value, str(e))
            self.connection_failed.emit(str(e))
