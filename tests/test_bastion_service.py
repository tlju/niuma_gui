import pytest
from unittest.mock import Mock, patch, MagicMock
from services.bastion_service import BastionService, BastionConnection, BastionChannel
from models.system_param import SystemParam


class TestBastionChannel:
    def test_bastion_channel_init(self):
        mock_channel = Mock()
        channel = BastionChannel(mock_channel, 1)
        
        assert channel.channel_id == 1
        assert channel.is_active == True
        assert channel.channel == mock_channel

    def test_bastion_channel_send(self):
        mock_channel = Mock()
        mock_channel.send.return_value = None
        channel = BastionChannel(mock_channel, 1)
        
        result = channel.send("test command\n")
        
        assert result == True
        mock_channel.send.assert_called_once_with("test command\n")

    def test_bastion_channel_send_failed(self):
        mock_channel = Mock()
        mock_channel.send.side_effect = Exception("Connection lost")
        channel = BastionChannel(mock_channel, 1)
        
        result = channel.send("test command\n")
        
        assert result == False
        assert channel.is_active == False

    def test_bastion_channel_close(self):
        mock_channel = Mock()
        channel = BastionChannel(mock_channel, 1)
        
        channel.close()
        
        mock_channel.close.assert_called_once()
        assert channel.is_active == False


class TestBastionConnection:
    def test_bastion_connection_init(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        assert conn.host == "192.168.1.100"
        assert conn.port == 22
        assert conn.username == "admin"
        assert conn.password == "password"
        assert conn.is_connected == False
        assert conn.is_authenticated == False

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_connect_success(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        result = conn.connect(timeout=30)
        
        assert result == True
        assert conn.is_connected == True
        mock_client.connect.assert_called_once()

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_connect_auth_failure(self, mock_ssh_client_class):
        import paramiko
        mock_client = Mock()
        mock_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "wrong_password")
        
        with pytest.raises(Exception) as exc_info:
            conn.connect(timeout=30)
        
        assert "认证失败" in str(exc_info.value)

    def test_disconnect(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.client = Mock()
        conn.is_connected = True
        
        conn.disconnect()
        
        assert conn.is_connected == False
        conn.client.close.assert_called_once()


class TestBastionService:
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
    def bastion_service(self, db_session):
        return BastionService(db_session)

    def test_get_bastion_config(self, bastion_service, db_session):
        host_param = SystemParam(
            param_name="堡垒机地址",
            param_code="BASTION_HOST",
            param_value="192.168.1.100:2222"
        )
        user_param = SystemParam(
            param_name="堡垒机用户名",
            param_code="BASTION_USER",
            param_value="admin"
        )
        password_param = SystemParam(
            param_name="堡垒机密码",
            param_code="BASTION_PASSWORD",
            param_value="secret123"
        )
        
        db_session.add(host_param)
        db_session.add(user_param)
        db_session.add(password_param)
        db_session.commit()
        
        config = bastion_service.get_bastion_config()
        
        assert config["host"] == "192.168.1.100"
        assert config["port"] == 2222
        assert config["username"] == "admin"
        assert config["password"] == "secret123"

    def test_get_bastion_config_missing_params(self, bastion_service):
        config = bastion_service.get_bastion_config()
        
        assert config["host"] is None
        assert config["username"] is None
        assert config["password"] is None

    def test_get_connection_status_not_exists(self, bastion_service):
        status = bastion_service.get_connection_status("nonexistent")
        
        assert status["exists"] == False
        assert status["connected"] == False

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_connect_with_explicit_params(self, mock_ssh_client_class, bastion_service):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = bastion_service.connect(
            connection_id="test_conn",
            host="192.168.1.100",
            port=2222,
            username="admin",
            password="secret"
        )
        
        assert conn.is_connected == True
        assert bastion_service.get_connection_status("test_conn")["exists"] == True

    def test_disconnect_all(self, bastion_service):
        mock_conn = Mock()
        bastion_service._connections["conn1"] = mock_conn
        bastion_service._connections["conn2"] = Mock()
        
        bastion_service.disconnect_all()
        
        mock_conn.disconnect.assert_called_once()
        assert len(bastion_service._connections) == 0
