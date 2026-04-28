import threading
from typing import Optional, Callable, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
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
            logger.info("BastionConnectionWorker: 开始连接堡垒机")
            
            def on_status_change(status: ConnectionStatus, message: str):
                if not self._is_cancelled:
                    logger.info(f"BastionConnectionWorker: 状态变更 - {status.value}: {message}")
                    self.status_changed.emit(status.value, message)
            
            def on_retry(attempt: int, error: str):
                if not self._is_cancelled:
                    logger.warning(f"BastionConnectionWorker: 重试 {attempt}/{self.max_retries} - {error}")
                    self.retry_attempt.emit(attempt, self.max_retries, error)
            
            self.connection = self.bastion_service.connect_with_retry(
                connection_id="default",
                max_retries=self.max_retries,
                retry_interval=self.retry_interval,
                on_status_change=on_status_change,
                on_retry=on_retry
            )
            
            if self._is_cancelled:
                logger.info("BastionConnectionWorker: 连接已被取消")
                self.bastion_service.disconnect("default")
                return
            
            self.status_changed.emit(ConnectionStatus.CONNECTED.value, "已连接，检测认证方式...")
            logger.info("BastionConnectionWorker: SSH连接成功，开始检测认证方式")
            
            auth_info = self.bastion_service.detect_auth_prompt("default")
            logger.info(f"BastionConnectionWorker: 认证检测结果 - needs_password={auth_info.get('needs_password')}, "
                        f"needs_otp={auth_info.get('needs_otp')}, needs_menu={auth_info.get('needs_menu')}")
            
            if auth_info.get("needs_password") or auth_info.get("needs_otp") or auth_info.get("needs_menu"):
                logger.info("BastionConnectionWorker: 需要二次认证，发出auth_required信号")
                self.auth_required.emit(auth_info)
            else:
                self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value, "认证成功")
                self.bastion_service.start_keepalive("default", min_channels=1, max_channels=5)
                logger.info("BastionConnectionWorker: 无需二次认证，连接完成")
                self.connection_success.emit()
                
        except Exception as e:
            logger.error(f"BastionConnectionWorker: 连接失败 - {e}")
            if not self._is_cancelled:
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
    
    def __init__(self, bastion_service: BastionService, 
                 otp_code: str = None, menu_selection: str = None, parent=None):
        super().__init__(parent)
        self.bastion_service = bastion_service
        self.otp_code = otp_code
        self.menu_selection = menu_selection
    
    def run(self):
        try:
            self.status_changed.emit(ConnectionStatus.AUTHENTICATING.value, "正在进行二次认证...")
            logger.info(f"BastionAuthWorker: 开始二次认证, has_otp_code={self.otp_code is not None}, "
                        f"menu_selection={self.menu_selection}")
            
            result = self.bastion_service.authenticate(
                connection_id="default",
                auth_type="otp",
                otp_code=self.otp_code,
                menu_selection=self.menu_selection
            )
            
            if result.get("has_server_list"):
                server_list = result.get("server_list", [])
                raw_output = result.get("output", "")
                logger.info(f"BastionAuthWorker: 认证成功，发现服务器列表({len(server_list)}台)")
                self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value, "认证成功，请选择目标服务器")
                self.server_list_available.emit(server_list, raw_output)
            else:
                self.status_changed.emit(ConnectionStatus.AUTHENTICATED.value, "认证成功")
                logger.info("BastionAuthWorker: 二次认证成功，启动保活")
                self.bastion_service.start_keepalive("default", min_channels=1, max_channels=5)
                self.auth_success.emit()
            
        except Exception as e:
            if str(e) == "OTP_RETRY":
                logger.warning("BastionAuthWorker: OTP验证码错误，需要重新输入")
                self.otp_retry_required.emit()
            else:
                logger.error(f"BastionAuthWorker: 二次认证失败 - {e}")
                self.status_changed.emit(ConnectionStatus.FAILED.value, str(e))
                self.auth_failed.emit(str(e))


class BastionManager(QObject):
    status_changed = pyqtSignal(str, str)
    connection_success = pyqtSignal()
    connection_failed = pyqtSignal(str)
    auth_required = pyqtSignal(dict, int)
    otp_retry_required = pyqtSignal(int)
    server_list_available = pyqtSignal(list, str)
    tunnel_created = pyqtSignal(dict)
    tunnel_closed = pyqtSignal(int)
    
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

    def create_tunnel(self, target_host: str, target_port: int = 22) -> dict:
        if not self.is_connected():
            raise Exception("堡垒机未连接")
        tunnel = self.bastion_service.create_tunnel("default", target_host, target_port)
        if tunnel:
            info = {
                "tunnel_id": tunnel.tunnel_id,
                "target_host": tunnel.target_host,
                "target_port": tunnel.target_port,
                "local_port": tunnel.local_port,
                "display": tunnel.get_display_info()
            }
            self.tunnel_created.emit(info)
            return info
        raise Exception("创建隧道失败")

    def close_tunnel(self, tunnel_id: int) -> bool:
        result = self.bastion_service.close_tunnel("default", tunnel_id)
        if result:
            self.tunnel_closed.emit(tunnel_id)
        return result

    def get_active_tunnels(self) -> list:
        return self.bastion_service.get_active_tunnels("default")
    
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
        self._cleanup_auth_worker()
        self.server_list_available.emit(server_list, raw_output)
    
    def _cleanup_auth_worker(self):
        if self._auth_worker is not None:
            try:
                self._auth_worker.status_changed.disconnect()
                self._auth_worker.auth_success.disconnect()
                self._auth_worker.auth_failed.disconnect()
                self._auth_worker.otp_retry_required.disconnect()
                self._auth_worker.server_list_available.disconnect()
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
