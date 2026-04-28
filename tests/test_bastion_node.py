import pytest
from unittest.mock import Mock, patch, MagicMock
from core.node_types import BastionNode, RemoteExecutionNode, NodeStatus, NodeResult
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
        assert bastion_node.category == "environment"
        assert bastion_node.display_name == "堡垒机连接"
        assert bastion_node.input_ports == 1
        assert bastion_node.output_ports == 1

    def test_bastion_node_inherits_from_remote_execution(self):
        assert issubclass(BastionNode, RemoteExecutionNode)

    def test_get_config_schema(self, bastion_node):
        schema = bastion_node.get_config_schema()
        
        assert schema["type"] == "object"
        assert "target_host" in schema["properties"]
        assert "operation" not in schema["properties"]

    def test_execute_without_db(self, bastion_node):
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "数据库会话未设置" in result.error

    def test_execute_without_target_host(self, bastion_node, db_session):
        bastion_node.set_services(db=db_session)
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "未指定目标主机地址" in result.error

    @patch('services.bastion_service.BastionService')
    def test_execute_success(self, mock_bastion_service_class, bastion_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.get_connection_status.return_value = {
            "authenticated": True
        }
        mock_channel = Mock()
        mock_channel.channel_id = 1
        mock_service.connect_to_host.return_value = mock_channel
        
        bastion_node.set_services(db=db_session)
        bastion_node.config = {
            "target_host": "192.168.1.200"
        }
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "已切换到远程执行环境" in result.output
        assert result.data["target_host"] == "192.168.1.200"
        mock_service.connect_to_host.assert_called_once()

    @patch('services.bastion_service.BastionService')
    def test_execute_without_bastion_connection(self, mock_bastion_service_class, bastion_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.get_connection_status.return_value = {
            "authenticated": False
        }
        
        bastion_node.set_services(db=db_session)
        bastion_node.config = {
            "target_host": "192.168.1.200"
        }
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "堡垒机未连接" in result.error

    @patch('services.bastion_service.BastionService')
    def test_execute_connect_host_failure(self, mock_bastion_service_class, bastion_node, db_session):
        mock_service = Mock()
        mock_bastion_service_class.return_value = mock_service
        mock_service.get_connection_status.return_value = {
            "authenticated": True
        }
        mock_service.connect_to_host.return_value = None
        
        bastion_node.set_services(db=db_session)
        bastion_node.config = {
            "target_host": "192.168.1.200"
        }
        
        result = bastion_node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "连接目标主机" in result.error

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
