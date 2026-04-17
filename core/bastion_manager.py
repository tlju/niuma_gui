import threading
from typing import Optional, Callable, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
from sqlalchemy.orm import Session
from services.bastion_service import BastionService, ConnectionStatus
from core.logger import get_logger

logger = get_logger(__name__)


class BastionConnectionWorker(QThread):
    status_changed = pyqtSignal(str, str)
    connection_failed = pyqtSignal(str)
    connection_success = pyqtSignal()
    auth_required = pyqtSignal(dict)
    retry_attempt = pyqtSignal(int, int, str)
    
    def __init__(self, bastion_service: BastionService, max_retries: int = 3, 
                 retry_interval: int = 5, parent=None):
        super().__init__(parent)
        self.bastion_service = bastion_service
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self._is_cancelled = False
        self.connection = None
    
    def run(self):
        try:
            self.status_changed.emit(ConnectionStatus.CONNECTING.value, "正在连接堡垒机...")
            
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
                self.bastion_service.start_keepalive("default", min_channels=1, max_channels=5)
                self.connection_success.emit()
                
        except Exception as e:
            if not self._is_cancelled:
                self.status_changed.emit(ConnectionStatus.FAILED.value, str(e))
                self.connection_failed.emit(str(e))
    
    def cancel(self):
        self._is_cancelled = True


class BastionAuthWorker(QThread):
    status_changed = pyqtSignal(str, str)
    auth_success = pyqtSignal()
    auth_failed = pyqtSignal(str)
    
    def __init__(self, bastion_service: BastionService, 
                 otp_code: str = None, parent=None):
        super().__init__(parent)
        self.bastion_service = bastion_service
        self.otp_code = otp_code
    
    def run(self):
        try:
            self.status_changed.emit(ConnectionStatus.AUTHENTICATING.value, "正在进行二次认证...")
            
            self.bastion_service.authenticate(
                connection_id="default",
                auth_type="otp",
                otp_code=self.otp_code
            )
            
            self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value, "认证成功")
            
            self.bastion_service.start_keepalive("default", min_channels=1, max_channels=5)
            
            self.auth_success.emit()
            
        except Exception as e:
            self.status_changed.emit(ConnectionStatus.FAILED.value, str(e))
            self.auth_failed.emit(str(e))


class BastionManager(QObject):
    status_changed = pyqtSignal(str, str)
    connection_success = pyqtSignal()
    connection_failed = pyqtSignal(str)
    auth_required = pyqtSignal(dict, int)
    
    MAX_AUTH_RETRIES = 5
    
    def __init__(self, db: Session, parent=None):
        super().__init__(parent)
        self.db = db
        self.bastion_service = BastionService(db)
        self._connection_worker: Optional[BastionConnectionWorker] = None
        self._auth_worker: Optional[BastionAuthWorker] = None
        self._status_monitor_timer: Optional[QTimer] = None
        self._is_auto_login = False
        self._auth_retry_count = 0
        self._auth_info: dict = {}
    
    def has_bastion_config(self) -> bool:
        return self.bastion_service.has_bastion_config()
    
    def start_auto_login(self, max_retries: int = 3, retry_interval: int = 5):
        if not self.has_bastion_config():
            logger.info("未配置堡垒机参数，跳过自动登录")
            return
        
        if self.is_connected():
            logger.info("堡垒机已连接，跳过自动登录")
            return
        
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
        self._auth_worker = BastionAuthWorker(
            self.bastion_service, otp_code
        )
        self._auth_worker.status_changed.connect(self._on_status_changed)
        self._auth_worker.auth_success.connect(self._on_auth_success)
        self._auth_worker.auth_failed.connect(self._on_auth_failed)
        self._auth_worker.start()
    
    def disconnect(self):
        if self._connection_worker and self._connection_worker.isRunning():
            self._connection_worker.cancel()
            self._connection_worker.wait(2000)
        
        if self._auth_worker and self._auth_worker.isRunning():
            self._auth_worker.wait(2000)
        
        self.bastion_service.disconnect("default")
        self._auth_retry_count = 0
        self.status_changed.emit(ConnectionStatus.DISCONNECTED.value, "已断开连接")
    
    def get_status(self) -> Dict[str, Any]:
        return self.bastion_service.get_connection_status("default")
    
    def is_connected(self) -> bool:
        status = self.get_status()
        return status.get("authenticated", False)
    
    def get_service(self) -> BastionService:
        return self.bastion_service
    
    def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        if not self.is_connected():
            raise Exception("堡垒机未连接")
        return self.bastion_service.execute_command("default", command, timeout)
    
    def connect_to_host(self, host: str, username: str = None, password: str = None):
        if not self.is_connected():
            raise Exception("堡垒机未连接")
        return self.bastion_service.connect_to_host("default", host, username, password)
    
    def _on_status_changed(self, status: str, message: str):
        self.status_changed.emit(status, message)
    
    def _on_connection_success(self):
        self.connection_success.emit()
        self._start_status_monitor()
    
    def _on_connection_failed(self, error: str):
        self.connection_failed.emit(error)
    
    def _on_auth_required(self, auth_info: dict):
        self._auth_info = auth_info
        self._auth_retry_count = 0
        self.auth_required.emit(auth_info, self._auth_retry_count)
    
    def _on_auth_success(self):
        self._auth_retry_count = 0
        self.connection_success.emit()
        self._start_status_monitor()
    
    def _on_auth_failed(self, error: str):
        self._auth_retry_count += 1
        
        if self._auth_retry_count < self.MAX_AUTH_RETRIES:
            logger.warning(f"二次认证失败 (尝试 {self._auth_retry_count}/{self.MAX_AUTH_RETRIES}): {error}")
            self.auth_required.emit(self._auth_info, self._auth_retry_count)
        else:
            logger.error(f"二次认证失败次数已达上限 ({self.MAX_AUTH_RETRIES}次): {error}")
            self.connection_failed.emit(f"动态口令验证失败次数已达上限，请稍后重试")
            self.bastion_service.disconnect("default")
            self._auth_retry_count = 0
    
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
