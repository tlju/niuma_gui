import pytest
from unittest.mock import Mock, patch, MagicMock
from core.node_types import (
    BaseNode, StartNode, EndNode, ScriptNode, CommandNode, DelayNode,
    ConditionNode, ParallelNode, MergeNode,
    NodeStatus, NodeResult, get_node_class, get_all_node_types
)
from core.workflow_engine import WorkflowExecutor


class TestNodeTypes:
    def test_start_node(self):
        node = StartNode(1, "开始节点")
        assert node.node_type == "start"
        assert node.input_ports == 0
        assert node.output_ports == 1

        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert "开始" in result.output

    def test_end_node(self):
        node = EndNode(1, "结束节点")
        assert node.node_type == "end"
        assert node.input_ports == 1
        assert node.output_ports == 0

        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert "结束" in result.output

    def test_delay_node(self):
        node = DelayNode(1, "延时节点", config={"delay_seconds": 0})
        assert node.node_type == "delay"

        result = node.execute()
        assert result.status == NodeStatus.SUCCESS

    def test_condition_node_true(self):
        node = ConditionNode(1, "条件节点", config={"condition": "True"})
        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert result.data.get("condition_result") == True

    def test_condition_node_false(self):
        node = ConditionNode(1, "条件节点", config={"condition": "False"})
        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert result.data.get("condition_result") == False

    def test_condition_node_with_input(self):
        node = ConditionNode(1, "条件节点", config={"condition": "input == 'test'"})
        result = node.execute(inputs={"output": "test"})
        assert result.status == NodeStatus.SUCCESS
        assert result.data.get("condition_result") == True


class TestCommandNode:
    def test_command_node_success(self):
        node = CommandNode(1, "命令节点", config={"command": "echo hello", "timeout": 10})
        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert "hello" in result.output

    def test_command_node_failure(self):
        node = CommandNode(1, "命令节点", config={"command": "exit 1", "timeout": 10})
        result = node.execute()
        assert result.status == NodeStatus.FAILED

    def test_command_node_no_command(self):
        node = CommandNode(1, "命令节点", config={"timeout": 10})
        result = node.execute()
        assert result.status == NodeStatus.FAILED
        assert "未配置执行命令" in result.error

    def test_command_node_config_schema(self):
        node = CommandNode(1, "命令节点")
        schema = node.get_config_schema()
        
        assert "command" in schema["properties"]
        assert "timeout" in schema["properties"]
        assert "working_dir" in schema["properties"]
        
        assert "command" in schema["required"]

    def test_command_node_with_input_variable(self):
        node = CommandNode(1, "命令节点", config={"command": "echo ${input}", "timeout": 10})
        result = node.execute(inputs={"output": "test_input"})
        assert result.status == NodeStatus.SUCCESS
        assert "test_input" in result.output


class TestScriptNode:
    def test_script_node_with_bash_script(self):
        node = ScriptNode(1, "Bash脚本节点", config={
            "script_content": "echo 'hello from bash'",
            "script_language": "bash",
            "timeout": 10
        })
        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert "hello from bash" in result.output

    def test_script_node_with_python_script(self):
        node = ScriptNode(1, "Python脚本节点", config={
            "script_content": "print('hello from python')",
            "script_language": "python",
            "timeout": 10
        })
        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert "hello from python" in result.output

    def test_script_node_no_content(self):
        node = ScriptNode(1, "脚本节点", config={"timeout": 10})
        result = node.execute()
        assert result.status == NodeStatus.FAILED
        assert "未找到脚本内容" in result.error

    def test_script_node_config_schema(self):
        node = ScriptNode(1, "脚本节点")
        schema = node.get_config_schema()
        
        assert "script_id" in schema["properties"]
        assert "script_content" in schema["properties"]
        assert "script_language" in schema["properties"]
        assert "script_name" in schema["properties"]
        assert "timeout" in schema["properties"]
        assert "working_dir" in schema["properties"]
        
        assert "script_id" in schema["required"]

    def test_script_node_with_input_variable(self):
        node = ScriptNode(1, "脚本节点", config={
            "script_content": "echo ${input}",
            "script_language": "bash",
            "timeout": 10
        })
        result = node.execute(inputs={"output": "test_input"})
        assert result.status == NodeStatus.SUCCESS
        assert "test_input" in result.output

    def test_script_node_result_includes_metadata(self):
        node = ScriptNode(1, "脚本节点", config={
            "script_content": "print('test')",
            "script_language": "python",
            "script_name": "test_script.py",
            "timeout": 10
        })
        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert result.data.get("script_name") == "test_script.py"
        assert result.data.get("script_language") == "python"


class TestGetNodeClass:
    def test_get_node_class(self):
        assert get_node_class("start") == StartNode
        assert get_node_class("end") == EndNode
        assert get_node_class("command") == CommandNode
        assert get_node_class("script") == ScriptNode
        assert get_node_class("unknown") == BaseNode

    def test_get_all_node_types(self):
        all_types = get_all_node_types()
        assert "start" in all_types
        assert "end" in all_types
        assert "command" in all_types
        assert "script" in all_types
        assert "delay" in all_types
        assert "condition" in all_types

        start_info = all_types["start"]
        assert start_info["display_name"] == "开始"
        assert start_info["category"] == "control"
        
        command_info = all_types["command"]
        assert command_info["display_name"] == "命令执行"
        assert command_info["category"] == "action"
        
        script_info = all_types["script"]
        assert script_info["display_name"] == "脚本执行"
        assert script_info["category"] == "action"


class TestWorkflowExecutor:
    def test_simple_workflow(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute()

        assert result["status"] == "success"
        assert result["success_count"] == 2

    def test_workflow_with_delay(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "delay", "name": "延时", "config": {"delay_seconds": 0}},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute()

        assert result["status"] == "success"
        assert result["success_count"] == 3

    def test_workflow_with_script(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "command", "name": "命令", "config": {"command": "echo test", "timeout": 10}},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute()

        assert result["status"] == "success"

    def test_workflow_cancel(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "delay", "name": "延时", "config": {"delay_seconds": 10}},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        executor.cancel()
        assert executor.is_cancelled == True

    def test_workflow_callbacks(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2}
        ]

        execution_updates = []
        log_entries = []

        def on_execution(update):
            execution_updates.append(update)

        def on_log(log):
            log_entries.append(log)

        executor = WorkflowExecutor(1, nodes, connections)
        executor.set_callbacks(on_execution, on_log)
        result = executor.execute()

        assert len(execution_updates) > 0
        assert len(log_entries) > 0

    def test_node_output_in_log(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "delay", "name": "延时节点", "config": {"delay_seconds": 0}},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]

        log_entries = []

        def on_log(log):
            log_entries.append(log)

        executor = WorkflowExecutor(1, nodes, connections)
        executor.set_callbacks(None, on_log)
        result = executor.execute()

        success_logs = [log for log in log_entries if "节点执行成功" in log["message"]]
        assert len(success_logs) > 0

        delay_success_log = next((log for log in success_logs if "延时节点" in log["message"]), None)
        assert delay_success_log is not None
        assert "延时0秒完成" in delay_success_log["message"]

    def test_parallel_execution(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "delay", "name": "延时1", "config": {"delay_seconds": 0}},
            {"id": 4, "node_type": "delay", "name": "延时2", "config": {"delay_seconds": 0}},
            {"id": 5, "node_type": "merge", "name": "合并"},
            {"id": 6, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 3, "target": 5},
            {"source": 4, "target": 5},
            {"source": 5, "target": 6}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute(max_workers=4)

        assert result["status"] == "success"

    def test_workflow_with_script_from_script_service(self):
        mock_script = Mock()
        mock_script.id = 1
        mock_script.content = "echo hello from script service"
        mock_script.language = "bash"
        mock_script.name = "test_script.sh"
        
        mock_script_service = Mock()
        mock_script_service.get_by_id = Mock(return_value=mock_script)
        
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "script", "name": "脚本", "config": {
                "script_id": 1,
                "script_content": "echo hello from script service",
                "script_language": "bash",
                "script_name": "test_script.sh",
                "timeout": 10
            }},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]

        executor = WorkflowExecutor(1, nodes, connections, script_service=mock_script_service)
        result = executor.execute()

        assert result["status"] == "success"
        
        node_2_result = result["node_results"][2]
        assert node_2_result["status"] == "success"
        assert "hello from script service" in node_2_result["output"]

    def test_workflow_with_python_script_from_script_service(self):
        mock_script = Mock()
        mock_script.id = 2
        mock_script.content = "print('hello from python script')"
        mock_script.language = "python"
        mock_script.name = "test_script.py"
        
        mock_script_service = Mock()
        mock_script_service.get_by_id = Mock(return_value=mock_script)
        
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "script", "name": "Python脚本", "config": {
                "script_id": 2,
                "script_content": "print('hello from python script')",
                "script_language": "python",
                "script_name": "test_script.py",
                "timeout": 10
            }},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]

        executor = WorkflowExecutor(1, nodes, connections, script_service=mock_script_service)
        result = executor.execute()

        assert result["status"] == "success"
        
        node_2_result = result["node_results"][2]
        assert node_2_result["status"] == "success"
        assert "hello from python script" in node_2_result["output"]

    def test_workflow_with_command_node(self):
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "command", "name": "命令", "config": {
                "command": "echo hello from command",
                "timeout": 10
            }},
            {"id": 3, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute()

        assert result["status"] == "success"
        
        node_2_result = result["node_results"][2]
        assert node_2_result["status"] == "success"
        assert "hello from command" in node_2_result["output"]


class TestNodeResult:
    def test_node_result_creation(self):
        result = NodeResult(
            status=NodeStatus.SUCCESS,
            output="test output",
            error="",
            data={"key": "value"}
        )

        assert result.status == NodeStatus.SUCCESS
        assert result.output == "test output"
        assert result.error == ""
        assert result.data == {"key": "value"}

    def test_node_result_default_values(self):
        result = NodeResult(status=NodeStatus.PENDING)

        assert result.output == ""
        assert result.error == ""
        assert result.data == {}


class TestVariableReplacement:
    def test_command_node_replace_dict_variable(self):
        from unittest.mock import Mock
        from models.data_dict_item import DataDictItem
        
        mock_dict_service = Mock()
        mock_item = DataDictItem(
            dict_code="script_language",
            item_code="python",
            item_name="Python"
        )
        mock_dict_service.get_dict_items.return_value = [mock_item]
        
        node = CommandNode(1, "Test Command", {
            "command": "echo @dict.script_language.Python"
        })
        node.set_services(dict_service=mock_dict_service)
        
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "python" in result.output
        mock_dict_service.get_dict_items.assert_called_once_with("script_language")
    
    def test_command_node_replace_param_variable(self):
        from unittest.mock import Mock
        from models.system_param import SystemParam
        
        mock_param_service = Mock()
        mock_param = SystemParam(
            param_name="测试参数",
            param_code="test_param",
            param_value="test_value_123"
        )
        mock_param_service.get_param_by_code.return_value = mock_param
        
        node = CommandNode(1, "Test Command", {
            "command": "echo @param.test_param"
        })
        node.set_services(param_service=mock_param_service)
        
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "test_value_123" in result.output
        mock_param_service.get_param_by_code.assert_called_once_with("test_param")
    
    def test_command_node_replace_multiple_variables(self):
        from unittest.mock import Mock
        from models.data_dict_item import DataDictItem
        from models.system_param import SystemParam
        
        mock_dict_service = Mock()
        mock_item = DataDictItem(
            dict_code="env",
            item_code="production",
            item_name="Production"
        )
        mock_dict_service.get_dict_items.return_value = [mock_item]
        
        mock_param_service = Mock()
        mock_param = SystemParam(
            param_name="版本",
            param_code="version",
            param_value="1.0.0"
        )
        mock_param_service.get_param_by_code.return_value = mock_param
        
        node = CommandNode(1, "Test Command", {
            "command": "echo Environment: @dict.env.Production, Version: @param.version"
        })
        node.set_services(dict_service=mock_dict_service, param_service=mock_param_service)
        
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "production" in result.output
        assert "1.0.0" in result.output
    
    def test_command_node_no_replacement_without_services(self):
        node = CommandNode(1, "Test Command", {
            "command": "echo @dict.test.value and @param.test"
        })
        
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "@dict.test.value" in result.output
        assert "@param.test" in result.output
    
    def test_script_node_replace_dict_variable(self):
        from unittest.mock import Mock
        from models.data_dict_item import DataDictItem
        
        mock_dict_service = Mock()
        mock_item = DataDictItem(
            dict_code="script_language",
            item_code="python",
            item_name="Python"
        )
        mock_dict_service.get_dict_items.return_value = [mock_item]
        
        node = ScriptNode(1, "Test Script", {
            "script_content": "echo @dict.script_language.Python",
            "script_language": "bash"
        })
        node.set_services(dict_service=mock_dict_service)
        
        result = node.execute()
        
        assert result.status == NodeStatus.SUCCESS
        assert "python" in result.output
        mock_dict_service.get_dict_items.assert_called_once_with("script_language")
