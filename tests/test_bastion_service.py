import pytest
from unittest.mock import Mock, patch, MagicMock
from services.bastion_service import BastionService, BastionConnection, BastionChannel, ConnectionStatus
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

    def test_bastion_channel_recv_ready(self):
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = True
        channel = BastionChannel(mock_channel, 1)
        
        assert channel.recv_ready() == True
        mock_channel.recv_ready.assert_called_once()

    def test_bastion_channel_recv_ready_inactive(self):
        mock_channel = Mock()
        channel = BastionChannel(mock_channel, 1)
        channel.is_active = False
        
        assert channel.recv_ready() == False

    def test_bastion_channel_recv(self):
        mock_channel = Mock()
        mock_channel.recv.return_value = b"test output"
        channel = BastionChannel(mock_channel, 1)
        
        data = channel.recv(4096)
        
        assert data == b"test output"
        mock_channel.recv.assert_called_once_with(4096)

    def test_bastion_channel_recv_failed(self):
        mock_channel = Mock()
        mock_channel.recv.side_effect = Exception("Read error")
        channel = BastionChannel(mock_channel, 1)
        
        data = channel.recv(4096)
        
        assert data == b""
        assert channel.is_active == False

    def test_bastion_channel_keepalive(self):
        mock_channel = Mock()
        mock_channel.send.return_value = None
        channel = BastionChannel(mock_channel, 1)
        
        result = channel.keepalive()
        
        assert result == True

    def test_bastion_channel_keepalive_failed(self):
        mock_channel = Mock()
        mock_channel.send.side_effect = Exception("Keepalive failed")
        channel = BastionChannel(mock_channel, 1)
        
        result = channel.keepalive()
        
        assert result == False
        assert channel.is_active == False


class TestParseServerList:
    def test_parse_server_list_with_colon_format(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        output = """
1: 192.168.1.10 Web服务器
2: 192.168.1.11 数据库服务器
3: 192.168.1.12 应用服务器
"""
        servers = conn._parse_server_list(output)
        
        assert len(servers) == 3
        assert servers[0]["index"] == "1"
        assert servers[0]["ip"] == "192.168.1.10"
        assert servers[0]["name"] == "Web服务器"
        assert servers[1]["ip"] == "192.168.1.11"

    def test_parse_server_list_with_space_format(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        output = """
  1: 192.168.1.10 Web服务器
  2: 192.168.1.11 数据库服务器
"""
        servers = conn._parse_server_list(output)
        
        assert len(servers) == 2
        assert servers[0]["index"] == "1"
        assert servers[0]["ip"] == "192.168.1.10"

    def test_parse_server_list_empty(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        output = "没有找到匹配的服务器"
        servers = conn._parse_server_list(output)
        
        assert len(servers) == 0

    def test_parse_server_list_mixed_content(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        output = """
欢迎使用堡垒机
请选择目标服务器:
1: 192.168.1.10 生产环境Web服务器
2: 192.168.1.11 测试环境数据库
输入序号选择:
"""
        servers = conn._parse_server_list(output)
        
        assert len(servers) == 2
        assert servers[0]["ip"] == "192.168.1.10"
        assert "生产环境" in servers[0]["name"]


class TestDetectAuthPrompt:
    @patch('services.bastion_service.paramiko.SSHClient')
    def test_detect_otp_prompt(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        with patch.object(conn, '_read_channel_output', return_value="2nd Password:"):
            auth_info = conn.detect_auth_prompt(timeout=5)
        
        assert auth_info["needs_otp"] == True

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_detect_menu_prompt(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        with patch.object(conn, '_read_channel_output', return_value="请选择目标服务器:"):
            auth_info = conn.detect_auth_prompt(timeout=5)
        
        assert auth_info["needs_menu"] == True


class TestSearchAndSelectAsset:
    @patch('services.bastion_service.paramiko.SSHClient')
    def test_search_and_select_asset_success(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        conn.status = ConnectionStatus.AUTHENTICATED
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        initial_output = "欢迎使用堡垒机\n"
        search_output = """
过滤条件：192.168.1.10
目标资产列表
序号: IP 地址                                  名称(说明) *
   1: 192.168.1.10                             目标服务器
请选择目标资产：
"""
        select_output = """
Connecting to any@目标服务器(192.168.1.10) ...
login:
"""
        
        call_count = [0]
        def mock_read_output(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return initial_output
            elif call_count[0] == 2:
                return search_output
            return select_output
        
        with patch.object(conn, '_read_channel_output', side_effect=mock_read_output):
            result = conn.search_and_select_asset("192.168.1.10", timeout=30)
        
        assert result["success"] == True
        mock_channel.send.assert_called()

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_search_and_select_asset_not_found(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        conn.status = ConnectionStatus.AUTHENTICATED
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        initial_output = "欢迎使用堡垒机\n"
        search_output = "未找到匹配的资产"
        
        call_count = [0]
        def mock_read_output(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return initial_output
            return search_output
        
        with patch.object(conn, '_read_channel_output', side_effect=mock_read_output):
            result = conn.search_and_select_asset("192.168.1.99", timeout=30)
        
        assert result["success"] == False
        assert "未找到" in result["error"]


class TestConnectToAsset:
    @patch('services.bastion_service.paramiko.SSHClient')
    def test_connect_to_asset_success(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        conn.status = ConnectionStatus.AUTHENTICATED
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        outputs = [
            "欢迎使用堡垒机\n",
            "过滤条件：192.168.1.10\n目标资产列表\n   1: 192.168.1.10 目标服务器\n请选择目标资产：",
            "Connecting to any@目标服务器(192.168.1.10) ...\nlogin:",
            "Password:",
            "Welcome to Ubuntu\n$ "
        ]
        output_index = [0]
        
        def mock_read_output(*args, **kwargs):
            idx = output_index[0]
            output_index[0] += 1
            return outputs[min(idx, len(outputs) - 1)]
        
        with patch.object(conn, '_read_channel_output', side_effect=mock_read_output):
            result = conn.connect_to_asset(
                target_ip="192.168.1.10",
                asset_username="testuser",
                asset_password="testpass",
                timeout=30
            )
        
        assert result["success"] == True
        assert result["channel"] is not None

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_connect_to_asset_permission_denied(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        conn.status = ConnectionStatus.AUTHENTICATED
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        outputs = [
            "欢迎使用堡垒机\n",
            "过滤条件：192.168.1.10\n目标资产列表\n   1: 192.168.1.10 目标服务器\n请选择目标资产：",
            "Connecting to any@目标服务器(192.168.1.10) ...\nlogin:",
            "Permission denied, please try again."
        ]
        output_index = [0]
        
        def mock_read_output(*args, **kwargs):
            idx = output_index[0]
            output_index[0] += 1
            return outputs[min(idx, len(outputs) - 1)]
        
        with patch.object(conn, '_read_channel_output', side_effect=mock_read_output):
            result = conn.connect_to_asset(
                target_ip="192.168.1.10",
                asset_username="testuser",
                asset_password="wrongpass",
                timeout=30
            )
        
        assert result["success"] == False
        assert "密码错误" in result["error"] or "权限被拒绝" in result["error"]


class TestExecuteCommandOnAsset:
    def test_execute_command_on_asset_success(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        mock_channel = Mock()
        mock_channel.is_active = True
        
        recv_ready_calls = [True, True, False]
        recv_ready_index = [0]
        def mock_recv_ready():
            idx = recv_ready_index[0]
            if idx < len(recv_ready_calls):
                recv_ready_index[0] += 1
                return recv_ready_calls[idx]
            return False
        
        mock_channel.recv_ready.side_effect = mock_recv_ready
        mock_channel.recv.return_value = b"total 0\ndrwxr-xr-x 2 root root 40 Apr 1 10:00 .\n"
        
        conn._current_session_channel = BastionChannel(mock_channel, 0, "192.168.1.10")
        
        result = conn.execute_command_on_asset("ls -la", timeout=10)
        
        assert result["success"] == True
        assert "total 0" in result["output"]

    def test_execute_command_on_asset_no_session(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn._current_session_channel = None
        
        result = conn.execute_command_on_asset("ls -la", timeout=10)
        
        assert result["success"] == False
        assert "没有活跃的资产会话" in result["error"]


class TestExitAssetSession:
    def test_exit_asset_session_success(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.client = Mock()
        
        mock_channel = Mock()
        mock_channel.is_active = True
        mock_channel.recv_ready.return_value = False
        
        conn._current_session_channel = BastionChannel(mock_channel, 0, "192.168.1.10")
        conn.channels = [conn._current_session_channel]
        
        mock_shell = Mock()
        mock_shell.recv_ready.return_value = False
        conn.client.invoke_shell.return_value = mock_shell
        
        with patch.object(conn, '_read_channel_output', return_value="已退出"):
            result = conn.exit_asset_session(timeout=10)
        
        assert result["success"] == True
        mock_channel.send.assert_called()

    def test_exit_asset_session_no_session(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn._current_session_channel = None
        
        result = conn.exit_asset_session(timeout=10)
        
        assert result["success"] == True
        assert "没有活跃的资产会话" in result["message"]


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
        from services.bastion_service import ConnectionStatus
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.client = Mock()
        conn.status = ConnectionStatus.AUTHENTICATED
        
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
        
        assert status["connected"] == False
        assert status["authenticated"] == False

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
        assert bastion_service.get_connection_status("test_conn")["connected"] == True

    def test_disconnect(self, bastion_service):
        mock_conn = Mock()
        bastion_service._connections["conn1"] = mock_conn
        
        bastion_service.disconnect("conn1")
        
        mock_conn.disconnect.assert_called_once()
        assert "conn1" not in bastion_service._connections


class TestProcessServerList:
    def test_process_server_list_filter_host_prefix(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        servers = [
            {"index": "1", "ip": "10.9.50.52", "name": "6273baac120b1"},
            {"index": "2", "ip": "10.9.50.52", "name": "host_1946189736078188544"},
            {"index": "3", "ip": "10.92.210.58", "name": "60448537b3e17"},
            {"index": "4", "ip": "10.92.210.59", "name": "host_12345"},
        ]
        
        processed = conn._process_server_list(servers)
        
        assert len(processed) == 2
        assert processed[0]["ip"] == "10.9.50.52"
        assert processed[1]["ip"] == "10.92.210.58"
        for server in processed:
            assert "host_" not in server["name"]

    def test_process_server_list_deduplicate_by_ip(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        servers = [
            {"index": "1", "ip": "10.9.50.52", "name": "server1"},
            {"index": "2", "ip": "10.9.50.52", "name": "server2"},
            {"index": "3", "ip": "10.92.210.58", "name": "server3"},
        ]
        
        processed = conn._process_server_list(servers)
        
        assert len(processed) == 2
        ips = [s["ip"] for s in processed]
        assert ips.count("10.9.50.52") == 1
        assert ips.count("10.92.210.58") == 1

    def test_process_server_list_combined_filter_and_dedup(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        servers = [
            {"index": "1", "ip": "10.9.50.52", "name": "valid_server1"},
            {"index": "2", "ip": "10.9.50.52", "name": "valid_server2"},
            {"index": "3", "ip": "10.92.210.58", "name": "host_invalid"},
            {"index": "4", "ip": "10.92.210.59", "name": "valid_server3"},
        ]
        
        processed = conn._process_server_list(servers)
        
        assert len(processed) == 2
        assert processed[0]["ip"] == "10.9.50.52"
        assert processed[1]["ip"] == "10.92.210.59"

    def test_process_server_list_empty(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        servers = []
        processed = conn._process_server_list(servers)
        
        assert len(processed) == 0

    def test_process_server_list_all_filtered(self):
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        
        servers = [
            {"index": "1", "ip": "10.9.50.52", "name": "host_123"},
            {"index": "2", "ip": "10.92.210.58", "name": "host_456"},
        ]
        
        processed = conn._process_server_list(servers)
        
        assert len(processed) == 0


class TestGlobalServerList:
    def test_set_and_get_global_server_list(self):
        servers = [
            {"index": "1", "ip": "10.9.50.52", "name": "server1"},
            {"index": "2", "ip": "10.92.210.58", "name": "server2"},
        ]
        
        BastionService.set_global_server_list(servers)
        
        result = BastionService.get_global_server_list()
        
        assert len(result) == 2
        assert result[0]["ip"] == "10.9.50.52"
        
        BastionService.clear_global_server_list()

    def test_has_global_server_list(self):
        BastionService.clear_global_server_list()
        
        assert BastionService.has_global_server_list() == False
        
        servers = [{"index": "1", "ip": "10.9.50.52", "name": "server1"}]
        BastionService.set_global_server_list(servers)
        
        assert BastionService.has_global_server_list() == True
        
        BastionService.clear_global_server_list()

    def test_clear_global_server_list(self):
        servers = [{"index": "1", "ip": "10.9.50.52", "name": "server1"}]
        BastionService.set_global_server_list(servers)
        
        BastionService.clear_global_server_list()
        
        assert BastionService.has_global_server_list() == False
        assert len(BastionService.get_global_server_list()) == 0

    def test_global_server_list_isolation(self):
        servers = [{"index": "1", "ip": "10.9.50.52", "name": "server1"}]
        BastionService.set_global_server_list(servers)
        
        result = BastionService.get_global_server_list()
        result.append({"index": "2", "ip": "10.92.210.58", "name": "server2"})
        
        original = BastionService.get_global_server_list()
        
        assert len(original) == 1
        
        BastionService.clear_global_server_list()


class TestDetectAuthPromptSimplified:
    @patch('services.bastion_service.paramiko.SSHClient')
    def test_detect_2nd_password_only(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        with patch.object(conn, '_read_channel_output', return_value="2nd Password:"):
            auth_info = conn.detect_auth_prompt(timeout=5)
        
        assert auth_info["needs_otp"] == True
        assert auth_info["needs_password"] == False

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_detect_menu_after_otp(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        output = """
********************************************************************************
*                             齐治交互终端 v3.3.10                             *
********************************************************************************

已选择：未分类资产
目标资产列表
序号: IP 地址                                  名称(说明) *
   1: 10.92.210.58                             60448537b3e17
-- 共 255 条记录。Ctrl-F：下一页 --
请选择目标资产：
"""
        with patch.object(conn, '_read_channel_output', return_value=output):
            auth_info = conn.detect_auth_prompt(timeout=5)
        
        assert auth_info["needs_menu"] == True
        assert auth_info["has_menu"] == True

    @patch('services.bastion_service.paramiko.SSHClient')
    def test_no_password_detection(self, mock_ssh_client_class):
        mock_client = Mock()
        mock_transport = Mock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_client_class.return_value = mock_client
        
        conn = BastionConnection("192.168.1.100", 22, "admin", "password")
        conn.connect(timeout=30)
        
        mock_channel = Mock()
        mock_channel.recv_ready.return_value = False
        mock_client.invoke_shell.return_value = mock_channel
        
        with patch.object(conn, '_read_channel_output', return_value="Password:"):
            auth_info = conn.detect_auth_prompt(timeout=5)
        
        assert auth_info["needs_password"] == False
        assert auth_info["needs_otp"] == False
