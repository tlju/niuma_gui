import pytest
from unittest.mock import Mock, patch, MagicMock
from core.node_types import RemoteExecutionNode, NodeStatus, NodeResult
from models.system_param import SystemParam


class TestRemoteExecutionNode:
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
    def remote_execution_node(self):
        return RemoteExecutionNode(1, "测试远程执行节点")

    def test_remote_execution_node_init(self, remote_execution_node):
        assert remote_execution_node.node_type == "remote_execution"
        assert remote_execution_node.category == "environment"
        assert remote_execution_node.display_name == "远程执行"
        assert remote_execution_node.input_ports == 1
        assert remote_execution_node.output_ports == 1

    def test_get_config_schema(self, remote_execution_node):
        schema = remote_execution_node.get_config_schema()
        
        assert schema["type"] == "object"
        assert "target_host" in schema["properties"]
        assert "operation" not in schema["properties"]

    def test_execute_without_db(self, remote_execution_node):
        result = remote_execution_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "数据库会话未设置" in result.error

    def test_execute_without_target_host(self, remote_execution_node, db_session):
        remote_execution_node.set_services(db=db_session)
        
        result = remote_execution_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "未指定目标主机地址" in result.error

    @patch('services.asset_service.AssetService')
    @patch('services.bastion_service.BastionService')
    def test_execute_success(self, mock_bastion_service_class, mock_asset_service_class, remote_execution_node, db_session):
        mock_bastion_service = Mock()
        mock_bastion_service_class.return_value = mock_bastion_service
        mock_bastion_service.get_connection_status.return_value = {
            "authenticated": True
        }
        
        mock_asset_service = Mock()
        mock_asset_service_class.return_value = mock_asset_service
        
        mock_asset = Mock()
        mock_asset.ip = "192.168.1.200"
        mock_asset.ipv6 = None
        mock_asset.username = "testuser"
        mock_asset.id = 1
        mock_asset_service.get_all.return_value = [mock_asset]
        mock_asset_service.get_password.return_value = "testpassword"
        
        mock_channel = Mock()
        mock_channel.channel_id = 1
        mock_bastion_service.connect_to_asset.return_value = {
            "success": True,
            "channel": mock_channel,
            "output": ""
        }
        
        remote_execution_node.set_services(db=db_session)
        remote_execution_node.config = {
            "target_host": "192.168.1.200"
        }
        
        result = remote_execution_node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "已切换到远程执行环境" in result.output
        assert result.data["target_host"] == "192.168.1.200"
        mock_bastion_service.connect_to_asset.assert_called_once()

    @patch('services.bastion_service.BastionService')
    def test_execute_without_bastion_connection(self, mock_bastion_service_class, remote_execution_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.get_connection_status.return_value = {
            "authenticated": False
        }
        
        remote_execution_node.set_services(db=db_session)
        remote_execution_node.config = {
            "target_host": "192.168.1.200"
        }
        
        result = remote_execution_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "堡垒机未连接" in result.error

    @patch('services.asset_service.AssetService')
    @patch('services.bastion_service.BastionService')
    def test_execute_connect_host_failure(self, mock_bastion_service_class, mock_asset_service_class, remote_execution_node, db_session):
        mock_bastion_service = Mock()
        mock_bastion_service_class.return_value = mock_bastion_service
        mock_bastion_service.get_connection_status.return_value = {
            "authenticated": True
        }
        
        mock_asset_service = Mock()
        mock_asset_service_class.return_value = mock_asset_service
        
        mock_asset = Mock()
        mock_asset.ip = "192.168.1.200"
        mock_asset.ipv6 = None
        mock_asset.username = "testuser"
        mock_asset.id = 1
        mock_asset_service.get_all.return_value = [mock_asset]
        mock_asset_service.get_password.return_value = "testpassword"
        
        mock_bastion_service.connect_to_asset.return_value = {
            "success": False,
            "error": "连接失败"
        }
        
        remote_execution_node.set_services(db=db_session)
        remote_execution_node.config = {
            "target_host": "192.168.1.200"
        }
        
        result = remote_execution_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "连接目标主机" in result.error

    def test_variable_replacement(self, remote_execution_node, db_session):
        host_param = SystemParam(
            param_name="堡垒机地址",
            param_code="BASTION_HOST",
            param_value="192.168.1.100"
        )
        db_session.add(host_param)
        db_session.commit()
        
        remote_execution_node.set_services(db=db_session)
        
        result = remote_execution_node._replace_variables("@param.BASTION_HOST")
        
        assert result == "192.168.1.100"

    def test_variable_replacement_nonexistent(self, remote_execution_node, db_session):
        remote_execution_node.set_services(db=db_session)
        
        result = remote_execution_node._replace_variables("@param.NONEXISTENT")
        
        assert result == "@param.NONEXISTENT"
