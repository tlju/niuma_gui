from __future__ import annotations

import threading
from typing import Optional, Callable, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from sqlalchemy.orm import Session
from services.bastion_service import BastionService, ConnectionStatus
from core.logger import get_logger
from core.config import settings
from core.workers import BastionConnectionWorker, BastionAuthWorker, AssetConnectionWorker

logger = get_logger(__name__)


class BastionManager(QObject):
    status_changed = pyqtSignal(str, str)
    connection_success = pyqtSignal()
    connection_failed = pyqtSignal(str)
    auth_required = pyqtSignal(dict, int)
    otp_retry_required = pyqtSignal(int)
    server_list_available = pyqtSignal(list, str)
    asset_connection_success = pyqtSignal(str)
    asset_connection_failed = pyqtSignal(str)

    MAX_AUTH_RETRIES = settings.BASTION_MAX_AUTH_RETRIES

    def __init__(self, db: Session, parent=None):
        super().__init__(parent)
        self.db = db
        self.bastion_service = BastionService(db)
        self._connection_worker: Optional[BastionConnectionWorker] = None
        self._auth_worker: Optional[BastionAuthWorker] = None
        self._asset_worker: Optional[AssetConnectionWorker] = None
        self._status_monitor_timer: Optional[QTimer] = None
        self._is_auto_login = False
        self._auth_retry_count = 0
        self._auth_info: dict = {}
        self._current_asset_ip: str = None
        self._server_list: list = []
        self._raw_output: str = ""

    def has_bastion_config(self) -> bool:
        return self.bastion_service.has_bastion_config()

    def start_auto_login(self, max_retries: int = 3, retry_interval: int = 5):
        if not self.has_bastion_config():
            logger.info("未配置堡垒机参数，跳过自动登录")
            return

        if self.is_connected():
            logger.info("堡垒机已连接，跳过自动登录")
            return

        logger.info(f"BastionManager: 启动自动登录, max_retries={max_retries}, retry_interval={retry_interval}")
        self._is_auto_login = True
        self._auth_retry_count = 0
        self._connection_worker = BastionConnectionWorker(
            self.bastion_service, max_retries, retry_interval
        )
        self._connection_worker.status_changed.connect(self._on_status_changed)
        self._connection_worker.connection_success.connect(self._on_connection_success)
        self._connection_worker.connection_failed.connect(self._on_connection_failed)
        self._connection_worker.auth_required.connect(self._on_auth_required)
        self._connection_worker.retry_attempt.connect(self._on_retry_attempt)
        self._connection_worker.start()

    def submit_auth(self, otp_code: str = None):
        logger.info(f"BastionManager: 提交二次认证, has_otp_code={otp_code is not None}")
        self._auth_worker = BastionAuthWorker(
            self.bastion_service, otp_code
        )
        self._auth_worker.status_changed.connect(self._on_status_changed)
        self._auth_worker.auth_success.connect(self._on_auth_success)
        self._auth_worker.auth_failed.connect(self._on_auth_failed)
        self._auth_worker.otp_retry_required.connect(self._on_otp_retry_required)
        self._auth_worker.server_list_available.connect(self._on_server_list_available)
        self._auth_worker.start()

    def select_server(self, menu_selection: str):
        logger.info(f"BastionManager: 选择服务器, menu_selection={menu_selection}")
        self._auth_worker = BastionAuthWorker(
            self.bastion_service, menu_selection=menu_selection
        )
        self._auth_worker.status_changed.connect(self._on_status_changed)
        self._auth_worker.auth_success.connect(self._on_auth_success)
        self._auth_worker.auth_failed.connect(self._on_auth_failed)
        self._auth_worker.otp_retry_required.connect(self._on_otp_retry_required)
        self._auth_worker.server_list_available.connect(self._on_server_list_available)
        self._auth_worker.start()

    def connect_to_asset(self, target_ip: str, asset_username: str, asset_password: str):
        if not self.is_connected():
            raise Exception("堡垒机未连接")

        logger.info(f"BastionManager: 连接资产 {target_ip}, username={asset_username}")
        self._current_asset_ip = target_ip

        self._asset_worker = AssetConnectionWorker(
            self.bastion_service, target_ip, asset_username, asset_password
        )
        self._asset_worker.status_changed.connect(self._on_status_changed)
        self._asset_worker.connection_success.connect(self._on_asset_connection_success)
        self._asset_worker.connection_failed.connect(self._on_asset_connection_failed)
        self._asset_worker.start()

    def execute_command_on_asset(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        if not self.is_connected():
            raise Exception("堡垒机未连接")
        return self.bastion_service.execute_command_on_asset("default", command, timeout)

    def exit_asset_session(self) -> Dict[str, Any]:
        if not self.is_connected():
            raise Exception("堡垒机未连接")

        result = self.bastion_service.exit_asset_session("default")
        self._current_asset_ip = None
        return result

    def disconnect(self):
        if self._connection_worker and self._connection_worker.isRunning():
            self._connection_worker.cancel()
            self._connection_worker.wait(2000)

        if self._auth_worker and self._auth_worker.isRunning():
            self._auth_worker.wait(2000)

        if self._asset_worker and self._asset_worker.isRunning():
            self._asset_worker.wait(2000)

        self.bastion_service.disconnect("default")
        self._auth_retry_count = 0
        self._current_asset_ip = None
        self._server_list = []
        self._raw_output = ""
        self.status_changed.emit(ConnectionStatus.DISCONNECTED.value, "已断开连接")

    def get_status(self) -> Dict[str, Any]:
        return self.bastion_service.get_connection_status("default")

    def is_connected(self) -> bool:
        status = self.get_status()
        return status.get("authenticated", False)

    def get_service(self) -> BastionService:
        return self.bastion_service

    def get_current_asset_ip(self) -> Optional[str]:
        return self._current_asset_ip

    def get_server_list(self) -> tuple:
        return self._server_list, self._raw_output

    def has_server_list(self) -> bool:
        return len(self._server_list) > 0

    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        if not self.is_connected():
            raise Exception("堡垒机未连接")
        return self.bastion_service.execute_command("default", command, timeout)

    def _on_status_changed(self, status: str, message: str):
        logger.info(f"BastionManager: 状态变更 - {status}: {message}")
        self.status_changed.emit(status, message)

    def _on_connection_success(self):
        logger.info("BastionManager: 堡垒机连接成功")
        self.connection_success.emit()
        self._start_status_monitor()

    def _on_connection_failed(self, error: str):
        logger.error(f"BastionManager: 堡垒机连接失败 - {error}")
        self.connection_failed.emit(error)

    def _on_auth_required(self, auth_info: dict):
        logger.info(f"BastionManager: 需要二次认证 - needs_password={auth_info.get('needs_password')}, "
                    f"needs_otp={auth_info.get('needs_otp')}, needs_menu={auth_info.get('needs_menu')}")
        self._auth_info = auth_info
        self._auth_retry_count = 0
        self.auth_required.emit(auth_info, self._auth_retry_count)

    def _on_auth_success(self):
        logger.info("BastionManager: 二次认证成功")
        self._auth_retry_count = 0
        self._cleanup_auth_worker()
        self.connection_success.emit()
        self._start_status_monitor()

    def _on_auth_failed(self, error: str):
        self._auth_retry_count += 1

        if self._auth_retry_count < self.MAX_AUTH_RETRIES:
            logger.warning(f"BastionManager: 二次认证失败 (尝试 {self._auth_retry_count}/{self.MAX_AUTH_RETRIES}): {error}")
            self.auth_required.emit(self._auth_info, self._auth_retry_count)
        else:
            logger.error(f"BastionManager: 二次认证失败次数已达上限 ({self.MAX_AUTH_RETRIES}次): {error}")
            self._cleanup_auth_worker()
            self.connection_failed.emit(f"动态口令验证失败次数已达上限，请稍后重试")
            self.bastion_service.disconnect("default")
            self._auth_retry_count = 0

    def _on_otp_retry_required(self):
        self._auth_retry_count += 1
        logger.info(f"BastionManager: OTP需要重新输入 (尝试 {self._auth_retry_count}/{self.MAX_AUTH_RETRIES})")
        if self._auth_retry_count < self.MAX_AUTH_RETRIES:
            self.otp_retry_required.emit(self._auth_retry_count)
        else:
            logger.error(f"BastionManager: OTP重试次数已达上限 ({self.MAX_AUTH_RETRIES}次)")
            self._cleanup_auth_worker()
            self.connection_failed.emit(f"动态口令验证失败次数已达上限，请稍后重试")
            self.bastion_service.disconnect("default")
            self._auth_retry_count = 0

    def _on_server_list_available(self, server_list: list, raw_output: str):
        logger.info(f"BastionManager: 服务器列表可用，共 {len(server_list)} 台")
        self._server_list = server_list
        self._raw_output = raw_output
        self._cleanup_auth_worker()
        self.server_list_available.emit(server_list, raw_output)

    def _on_asset_connection_success(self, target_ip: str):
        logger.info(f"BastionManager: 资产连接成功 - {target_ip}")
        self._current_asset_ip = target_ip
        self.asset_connection_success.emit(target_ip)

    def _on_asset_connection_failed(self, error: str):
        logger.error(f"BastionManager: 资产连接失败 - {error}")
        self._current_asset_ip = None
        self.asset_connection_failed.emit(error)

    def _cleanup_auth_worker(self):
        if self._auth_worker is not None:
            try:
                self._auth_worker.status_changed.disconnect(self._on_status_changed)
                self._auth_worker.auth_success.disconnect(self._on_auth_success)
                self._auth_worker.auth_failed.disconnect(self._on_auth_failed)
                self._auth_worker.otp_retry_required.disconnect(self._on_otp_retry_required)
                self._auth_worker.server_list_available.disconnect(self._on_server_list_available)
            except TypeError:
                pass
            if self._auth_worker.isRunning():
                self._auth_worker.wait(1000)
            self._auth_worker.deleteLater()
            self._auth_worker = None

    def _on_retry_attempt(self, attempt: int, max_retries: int, error: str):
        logger.info(f"堡垒机连接重试 {attempt}/{max_retries}: {error}")

    def _start_status_monitor(self):
        if self._status_monitor_timer:
            self._status_monitor_timer.stop()

        self._status_monitor_timer = QTimer(self)
        self._status_monitor_timer.timeout.connect(self._check_connection_status)
        self._status_monitor_timer.start(30000)

    def _check_connection_status(self):
        status = self.get_status()
        if not status.get("authenticated", False):
            self.status_changed.emit(ConnectionStatus.DISCONNECTED.value, "连接已断开")
            if self._status_monitor_timer:
                self._status_monitor_timer.stop()
