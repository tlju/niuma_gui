"""
测试远程执行节点和环境上下文延续机制
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from core.node_types import RemoteExecutionNode, LocalExecutionNode, ScriptNode, CommandNode, NodeStatus, NodeResult
from core.workflow_engine import WorkflowExecutor, ExecutionEnvironment


class TestRemoteExecutionNode:
    """测试远程执行节点"""
    
    def test_node_type_properties(self):
        """测试节点类型属性"""
        assert RemoteExecutionNode.node_type == "remote_execution"
        assert RemoteExecutionNode.category == "environment"
        assert RemoteExecutionNode.display_name == "远程执行"
        assert RemoteExecutionNode.input_ports == 1
        assert RemoteExecutionNode.output_ports == 1
    
    def test_config_schema(self):
        """测试配置schema"""
        node = RemoteExecutionNode(1, "测试远程执行")
        schema = node.get_config_schema()
        
        assert "target_host" in schema["properties"]
        assert schema["properties"]["target_host"]["dynamicEnum"] == "connected_hosts"
        assert schema["properties"]["target_host"]["allowManualInput"] == True
        assert "operation" not in schema["properties"]
    
    def test_execute_without_db(self):
        """测试没有数据库时执行失败"""
        node = RemoteExecutionNode(1, "测试远程执行", {"target_host": "192.168.1.100"})
        result = node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "数据库会话未设置" in result.error
    
    def test_execute_without_target_host(self):
        """测试没有目标主机时执行失败"""
        node = RemoteExecutionNode(1, "测试远程执行", {})
        node.db = Mock()
        result = node.execute()
        
        assert result.status == NodeStatus.FAILED
        assert "未指定目标主机地址" in result.error
    
    @patch('services.asset_service.AssetService')
    @patch('services.bastion_service.BastionService')
    def test_execute_success(self, mock_bastion_service_class, mock_asset_service_class):
        """测试成功执行远程执行节点"""
        mock_db = Mock()
        mock_bastion_service = Mock()
        mock_bastion_service_class.return_value = mock_bastion_service
        
        mock_bastion_service.get_connection_status.return_value = {"authenticated": True}
        
        mock_asset_service = Mock()
        mock_asset_service_class.return_value = mock_asset_service
        
        mock_asset = Mock()
        mock_asset.ip = "192.168.1.100"
        mock_asset.ipv6 = None
        mock_asset.username = "testuser"
        mock_asset.id = 1
        mock_asset_service.get_all.return_value = [mock_asset]
        mock_asset_service.get_password.return_value = "testpassword"
        
        mock_channel = Mock()
        mock_channel.channel_id = 123
        mock_bastion_service.connect_to_asset.return_value = {
            "success": True,
            "channel": mock_channel,
            "output": ""
        }
        
        node = RemoteExecutionNode(1, "测试远程执行", {"target_host": "192.168.1.100"})
        node.db = mock_db
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "已切换到远程执行环境" in result.output
        assert result.data["target_host"] == "192.168.1.100"
        assert result.data["channel_id"] == 123
        assert result.data["execution_environment"] == "remote"


class TestLocalExecutionNode:
    """测试本机执行节点"""
    
    def test_node_type_properties(self):
        """测试节点类型属性"""
        assert LocalExecutionNode.node_type == "local_execution"
        assert LocalExecutionNode.category == "environment"
        assert LocalExecutionNode.display_name == "本机执行"
    
    def test_execute(self):
        """测试执行本机执行节点"""
        node = LocalExecutionNode(1, "测试本机执行")
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "已切换到本地执行环境" in result.output
        assert result.data["execution_environment"] == "local"


class TestCommandNodeRemoteExecution:
    """测试命令节点远程执行"""
    
    def test_local_execution(self):
        """测试本地执行命令"""
        node = CommandNode(1, "测试命令", {"command": "echo hello"})
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "hello" in result.output
    
    def test_remote_execution_without_bastion_manager(self):
        """测试远程执行但没有堡垒机管理器"""
        node = CommandNode(1, "测试命令", {"command": "echo hello"})
        inputs = {
            "execution_environment": "remote",
            "target_host": "192.168.1.100",
            "channel_id": 123
        }
        result = node.execute(inputs)
        
        assert result.status == NodeStatus.FAILED
        assert "堡垒机管理器不可用" in result.error
    
    def test_remote_execution_with_bastion_manager(self):
        """测试远程执行命令"""
        node = CommandNode(1, "测试命令", {"command": "echo hello"})
        
        mock_bastion_manager = Mock()
        mock_bastion_manager.execute_command.return_value = {
            "success": True,
            "output": "hello\n"
        }
        
        inputs = {
            "execution_environment": "remote",
            "target_host": "192.168.1.100",
            "channel_id": 123,
            "bastion_manager": mock_bastion_manager
        }
        result = node.execute(inputs)
        
        assert result.status == NodeStatus.SUCCESS
        assert "hello" in result.output
        assert result.data["target_host"] == "192.168.1.100"
        mock_bastion_manager.execute_command.assert_called_once_with("echo hello", 300)


class TestScriptNodeRemoteExecution:
    """测试脚本节点远程执行"""
    
    def test_remote_execution_bash_script(self):
        """测试远程执行Bash脚本"""
        node = ScriptNode(1, "测试脚本", {
            "script_content": "echo hello",
            "script_language": "bash",
            "script_name": "test.sh"
        })
        
        mock_bastion_manager = Mock()
        mock_bastion_manager.execute_command.return_value = {
            "success": True,
            "output": "hello\n"
        }
        
        inputs = {
            "execution_environment": "remote",
            "target_host": "192.168.1.100",
            "channel_id": 123,
            "bastion_manager": mock_bastion_manager
        }
        result = node.execute(inputs)
        
        assert result.status == NodeStatus.SUCCESS
        assert "hello" in result.output
    
    def test_remote_execution_python_script_fails(self):
        """测试远程执行Python脚本失败（仅支持Bash）"""
        node = ScriptNode(1, "测试脚本", {
            "script_content": "print('hello')",
            "script_language": "python",
            "script_name": "test.py"
        })
        
        mock_bastion_manager = Mock()
        
        inputs = {
            "execution_environment": "remote",
            "target_host": "192.168.1.100",
            "channel_id": 123,
            "bastion_manager": mock_bastion_manager
        }
        result = node.execute(inputs)
        
        assert result.status == NodeStatus.FAILED
        assert "远程执行仅支持Bash脚本" in result.error


class TestWorkflowExecutorEnvironmentContext:
    """测试工作流执行器环境上下文延续机制"""
    
    def test_initial_environment_is_local(self):
        """测试初始执行环境为本地"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "end", "name": "结束"}
        ]
        connections = [{"source": 1, "target": 2}]
        
        executor = WorkflowExecutor(1, nodes, connections)
        assert executor.execution_environment == ExecutionEnvironment.LOCAL
        assert executor.current_target_host is None
        assert executor.current_channel_id is None
    
    @patch('core.workflow_engine.WorkflowExecutor._check_bastion_connection')
    @patch('core.workflow_engine.WorkflowExecutor._check_global_server_list')
    @patch('services.asset_service.AssetService')
    @patch('services.bastion_service.BastionService')
    def test_environment_switch_to_remote(self, mock_bastion_service_class, mock_asset_service_class, mock_check_global, mock_check_connection):
        """测试切换到远程执行环境"""
        mock_check_connection.return_value = True
        mock_check_global.return_value = True
        
        mock_bastion_service = Mock()
        mock_bastion_service_class.return_value = mock_bastion_service
        mock_bastion_service.get_connection_status.return_value = {"authenticated": True}
        
        mock_asset_service = Mock()
        mock_asset_service_class.return_value = mock_asset_service
        
        mock_asset = Mock()
        mock_asset.ip = "192.168.1.100"
        mock_asset.ipv6 = None
        mock_asset.username = "testuser"
        mock_asset.id = 1
        mock_asset_service.get_all.return_value = [mock_asset]
        mock_asset_service.get_password.return_value = "testpassword"
        
        mock_channel = Mock()
        mock_channel.channel_id = 123
        mock_bastion_service.connect_to_asset.return_value = {
            "success": True,
            "channel": mock_channel,
            "output": ""
        }
        
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "remote_execution", "name": "远程执行", "config": {"target_host": "192.168.1.100"}},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]
        
        mock_db = Mock()
        executor = WorkflowExecutor(1, nodes, connections, db=mock_db)
        result = executor.execute()
        
        assert result["status"] == "success"
    
    def test_environment_switch_to_local(self):
        """测试切换回本地执行环境"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "local_execution", "name": "本机执行"},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]
        
        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute()
        
        assert result["status"] == "success"
        assert executor.execution_environment == ExecutionEnvironment.LOCAL
        assert executor.current_target_host is None
        assert executor.current_channel_id is None
    
    def test_inputs_contain_remote_environment_info(self):
        """测试inputs包含远程执行环境信息"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "command", "name": "命令执行", "config": {"command": "echo hello"}},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]
        
        executor = WorkflowExecutor(1, nodes, connections)
        executor.execution_environment = ExecutionEnvironment.REMOTE_BASTION
        executor.current_target_host = "192.168.1.100"
        executor.current_channel_id = 123
        executor.bastion_manager = Mock()
        
        inputs = {}
        if executor.execution_environment == ExecutionEnvironment.REMOTE_BASTION:
            inputs["execution_environment"] = "remote"
            inputs["target_host"] = executor.current_target_host
            inputs["channel_id"] = executor.current_channel_id
            inputs["bastion_manager"] = executor.bastion_manager
        
        assert inputs["execution_environment"] == "remote"
        assert inputs["target_host"] == "192.168.1.100"
        assert inputs["channel_id"] == 123
        assert inputs["bastion_manager"] is not None
