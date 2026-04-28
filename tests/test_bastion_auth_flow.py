import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtCore import QThread, QTimer
from core.bastion_manager import BastionManager, BastionConnectionWorker, BastionAuthWorker
from services.bastion_service import ConnectionStatus
import time


class TestBastionAuthWorker:
    """测试堡垒机认证工作线程"""
    
    def test_auth_worker_signals(self):
        """测试认证工作线程的信号定义"""
        worker = BastionAuthWorker(Mock())
        assert hasattr(worker, 'status_changed')
        assert hasattr(worker, 'auth_success')
        assert hasattr(worker, 'auth_failed')
        assert hasattr(worker, 'otp_retry_required')
        assert hasattr(worker, 'server_list_available')
    
    @patch('services.bastion_service.BastionService')
    def test_auth_worker_success(self, mock_bastion_service_class):
        """测试认证工作线程成功完成认证"""
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.authenticate.return_value = {
            "authenticated": True,
            "has_server_list": False,
            "server_list": [],
            "output": "Welcome"
        }
        
        worker = BastionAuthWorker(mock_service, otp_code="123456")
        
        signals_received = []
        worker.status_changed.connect(lambda s, m: signals_received.append(('status', s)))
        worker.auth_success.connect(lambda: signals_received.append(('success',)))
        
        worker.run()
        
        assert ('success',) in signals_received
        mock_service.authenticate.assert_called_once()
    
    @patch('services.bastion_service.BastionService')
    def test_auth_worker_with_server_list(self, mock_bastion_service_class):
        """测试认证工作线程返回服务器列表"""
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.authenticate.return_value = {
            "authenticated": True,
            "has_server_list": True,
            "server_list": [{"index": "1", "ip": "192.168.1.1", "name": "Server1"}],
            "output": "Select server"
        }
        
        worker = BastionAuthWorker(mock_service, otp_code="123456")
        
        signals_received = []
        worker.server_list_available.connect(lambda s, o: signals_received.append(('server_list', s)))
        
        worker.run()
        
        assert len(signals_received) == 1
        assert signals_received[0][0] == 'server_list'
        assert len(signals_received[0][1]) == 1
    
    @patch('services.bastion_service.BastionService')
    def test_auth_worker_otp_retry(self, mock_bastion_service_class):
        """测试认证工作线程OTP重试"""
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.authenticate.side_effect = Exception("OTP_RETRY")
        
        worker = BastionAuthWorker(mock_service, otp_code="123456")
        
        signals_received = []
        worker.otp_retry_required.connect(lambda: signals_received.append(('otp_retry',)))
        
        worker.run()
        
        assert ('otp_retry',) in signals_received
    
    @patch('services.bastion_service.BastionService')
    def test_auth_worker_auth_failed(self, mock_bastion_service_class):
        """测试认证工作线程认证失败"""
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.authenticate.side_effect = Exception("认证失败")
        
        worker = BastionAuthWorker(mock_service, otp_code="123456")
        
        signals_received = []
        worker.auth_failed.connect(lambda e: signals_received.append(('failed', e)))
        
        worker.run()
        
        assert len(signals_received) == 1
        assert signals_received[0][0] == 'failed'


class TestBastionManager:
    """测试堡垒机管理器"""
    
    @pytest.fixture
    def db_session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models.base import Base
        
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def bastion_manager(self, db_session):
        return BastionManager(db_session)
    
    def test_bastion_manager_init(self, bastion_manager):
        """测试堡垒机管理器初始化"""
        assert bastion_manager.MAX_AUTH_RETRIES == 5
        assert bastion_manager._auth_retry_count == 0
        assert bastion_manager._auth_worker is None
        assert bastion_manager._connection_worker is None
    
    def test_get_status(self, bastion_manager):
        """测试获取连接状态"""
        status = bastion_manager.get_status()
        assert "authenticated" in status
        assert "connected" in status
    
    def test_is_connected(self, bastion_manager):
        """测试连接状态检查"""
        assert bastion_manager.is_connected() == False
    
    @patch('services.bastion_service.BastionService.has_bastion_config')
    def test_has_bastion_config(self, mock_has_config, bastion_manager):
        """测试堡垒机配置检查"""
        mock_has_config.return_value = True
        assert bastion_manager.has_bastion_config() == True
        mock_has_config.return_value = False
        assert bastion_manager.has_bastion_config() == False
    
    def test_cleanup_auth_worker(self, bastion_manager):
        """测试清理认证工作线程"""
        mock_worker = Mock()
        mock_worker.isRunning.return_value = False
        bastion_manager._auth_worker = mock_worker
        
        bastion_manager._cleanup_auth_worker()
        
        assert bastion_manager._auth_worker is None
        mock_worker.deleteLater.assert_called_once()
    
    def test_cleanup_auth_worker_with_running_thread(self, bastion_manager):
        """测试清理正在运行的认证工作线程"""
        mock_worker = Mock()
        mock_worker.isRunning.return_value = True
        bastion_manager._auth_worker = mock_worker
        
        bastion_manager._cleanup_auth_worker()
        
        assert bastion_manager._auth_worker is None
        mock_worker.wait.assert_called_once_with(1000)
    
    def test_on_auth_success(self, bastion_manager):
        """测试认证成功回调"""
        signals_received = []
        bastion_manager.connection_success.connect(lambda: signals_received.append('success'))
        
        mock_worker = Mock()
        mock_worker.isRunning.return_value = False
        bastion_manager._auth_worker = mock_worker
        
        bastion_manager._on_auth_success()
        
        assert 'success' in signals_received
        assert bastion_manager._auth_retry_count == 0
    
    def test_on_auth_failed_retry(self, bastion_manager):
        """测试认证失败重试"""
        signals_received = []
        bastion_manager.auth_required.connect(lambda a, r: signals_received.append(('retry', r)))
        
        bastion_manager._auth_info = {"needs_otp": True}
        bastion_manager._on_auth_failed("认证失败")
        
        assert bastion_manager._auth_retry_count == 1
        assert ('retry', 1) in signals_received
    
    def test_on_auth_failed_max_retries(self, bastion_manager):
        """测试认证失败达到最大重试次数"""
        signals_received = []
        bastion_manager.connection_failed.connect(lambda e: signals_received.append(('failed', e)))
        
        bastion_manager._auth_info = {"needs_otp": True}
        bastion_manager._auth_retry_count = 4
        
        bastion_manager._on_auth_failed("认证失败")
        
        assert len(signals_received) == 1
        assert signals_received[0][0] == 'failed'
    
    def test_on_otp_retry_required(self, bastion_manager):
        """测试OTP重试请求"""
        signals_received = []
        bastion_manager.otp_retry_required.connect(lambda r: signals_received.append(('otp_retry', r)))
        
        bastion_manager._on_otp_retry_required()
        
        assert bastion_manager._auth_retry_count == 1
        assert ('otp_retry', 1) in signals_received
    
    def test_on_server_list_available(self, bastion_manager):
        """测试服务器列表可用"""
        signals_received = []
        bastion_manager.server_list_available.connect(lambda s, o: signals_received.append(('servers', s)))
        
        mock_worker = Mock()
        mock_worker.isRunning.return_value = False
        bastion_manager._auth_worker = mock_worker
        
        server_list = [{"index": "1", "ip": "192.168.1.1", "name": "Server1"}]
        bastion_manager._on_server_list_available(server_list, "raw output")
        
        assert ('servers', server_list) in signals_received
        assert bastion_manager._auth_worker is None


class TestBastionManagerSignalChain:
    """测试堡垒机管理器信号链"""
    
    @pytest.fixture
    def db_session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models.base import Base
        
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def bastion_manager(self, db_session):
        return BastionManager(db_session)
    
    def test_auth_success_signal_chain(self, bastion_manager):
        """测试认证成功信号链"""
        connection_success_received = []
        bastion_manager.connection_success.connect(lambda: connection_success_received.append(True))
        
        mock_worker = Mock()
        mock_worker.isRunning.return_value = False
        bastion_manager._auth_worker = mock_worker
        
        bastion_manager._on_auth_success()
        
        assert len(connection_success_received) == 1
        assert bastion_manager._auth_worker is None
    
    def test_auth_failed_signal_chain(self, bastion_manager):
        """测试认证失败信号链"""
        auth_required_received = []
        bastion_manager.auth_required.connect(lambda a, r: auth_required_received.append((a, r)))
        
        bastion_manager._auth_info = {"needs_otp": True}
        
        for i in range(4):
            bastion_manager._on_auth_failed("认证失败")
        
        assert bastion_manager._auth_retry_count == 4
        assert len(auth_required_received) == 4
    
    def test_max_reaches_disconnect(self, bastion_manager):
        """测试达到最大重试次数后断开连接"""
        connection_failed_received = []
        bastion_manager.connection_failed.connect(lambda e: connection_failed_received.append(e))
        
        bastion_manager._auth_info = {"needs_otp": True}
        bastion_manager._auth_retry_count = 4
        
        mock_worker = Mock()
        mock_worker.isRunning.return_value = False
        bastion_manager._auth_worker = mock_worker
        
        bastion_manager._on_auth_failed("认证失败")
        
        assert len(connection_failed_received) == 1
        assert "上限" in connection_failed_received[0]
