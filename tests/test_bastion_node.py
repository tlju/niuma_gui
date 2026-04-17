import pytest
from unittest.mock import Mock, patch, MagicMock
from core.node_types import BastionNode, NodeStatus, NodeResult
from models.system_param import SystemParam


class TestBastionNode:
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
    def bastion_node(self):
        return BastionNode(1, "测试堡垒机节点")

    def test_bastion_node_init(self, bastion_node):
        assert bastion_node.node_type == "bastion"
        assert bastion_node.category == "action"
        assert bastion_node.display_name == "堡垒机连接"
        assert bastion_node.input_ports == 1
        assert bastion_node.output_ports == 1

    def test_get_config_schema(self, bastion_node):
        schema = bastion_node.get_config_schema()
        
        assert schema["type"] == "object"
        assert "operation" in schema["properties"]
        assert "connection_id" in schema["properties"]
        assert "auth_type" in schema["properties"]
        assert "keepalive_enabled" in schema["properties"]
        assert "min_channels" in schema["properties"]
        assert "max_channels" in schema["properties"]

    def test_execute_without_db(self, bastion_node):
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "数据库会话未设置" in result.error

    def test_execute_without_operation(self, bastion_node, db_session):
        bastion_node.set_services(db=db_session)
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "未指定操作类型" in result.error

    @patch('services.bastion_service.BastionService')
    def test_execute_connect_operation(self, mock_bastion_service_class, bastion_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.connect.return_value = Mock(is_connected=True)
        mock_service.authenticate.return_value = True
        mock_service.get_connection_status.return_value = {
            "host": "192.168.1.100",
            "username": "admin",
            "channels": 1
        }
        
        bastion_node.set_services(db=db_session)
        bastion_node.config = {
            "operation": "connect",
            "connection_id": "test",
            "auth_type": "password",
            "keepalive_enabled": False
        }
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "堡垒机连接成功" in result.output
        mock_service.connect.assert_called_once()
        mock_service.authenticate.assert_called_once()

    @patch('services.bastion_service.BastionService')
    def test_execute_disconnect_operation(self, mock_bastion_service_class, bastion_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        
        bastion_node.set_services(db=db_session)
        bastion_node.config = {
            "operation": "disconnect",
            "connection_id": "test"
        }
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "已断开" in result.output
        mock_service.disconnect.assert_called_once_with("test")

    @patch('services.bastion_service.BastionService')
    def test_execute_status_operation(self, mock_bastion_service_class, bastion_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.get_connection_status.return_value = {
            "exists": True,
            "connected": True,
            "channels": 2
        }
        
        bastion_node.set_services(db=db_session)
        bastion_node.config = {
            "operation": "status",
            "connection_id": "test"
        }
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        mock_service.get_connection_status.assert_called_once_with("test")

    @patch('services.bastion_service.BastionService')
    def test_execute_command_operation(self, mock_bastion_service_class, bastion_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.execute_command.return_value = {
            "success": True,
            "output": "total 0\ndrwxr-xr-x",
            "command": "ls -la"
        }
        
        bastion_node.set_services(db=db_session)
        bastion_node.config = {
            "operation": "execute",
            "connection_id": "test",
            "command": "ls -la"
        }
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "命令执行成功" in result.output
        mock_service.execute_command.assert_called_once()

    def test_variable_replacement(self, bastion_node, db_session):
        host_param = SystemParam(
            param_name="堡垒机地址",
            param_code="BASTION_HOST",
            param_value="192.168.1.100"
        )
        db_session.add(host_param)
        db_session.commit()
        
        bastion_node.set_services(db=db_session)
        
        result = bastion_node._replace_variables("@param.BASTION_HOST")
        
        assert result == "192.168.1.100"

    def test_variable_replacement_nonexistent(self, bastion_node, db_session):
        bastion_node.set_services(db=db_session)
        
        result = bastion_node._replace_variables("@param.NONEXISTENT")
        
        assert result == "@param.NONEXISTENT"
