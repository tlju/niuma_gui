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


class TestTopologicalSort:
    def test_simple_linear_workflow(self):
        from gui.pages.workflow_page import topological_sort_nodes
        
        nodes = [
            {"id": 3, "name": "结束"},
            {"id": 1, "name": "开始"},
            {"id": 2, "name": "中间"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3}
        ]
        
        result = topological_sort_nodes(nodes, connections)
        
        assert result.index(1) < result.index(2)
        assert result.index(2) < result.index(3)
    
    def test_parallel_workflow(self):
        from gui.pages.workflow_page import topological_sort_nodes
        
        nodes = [
            {"id": 1, "name": "开始"},
            {"id": 2, "name": "并行"},
            {"id": 3, "name": "分支1"},
            {"id": 4, "name": "分支2"},
            {"id": 5, "name": "合并"},
            {"id": 6, "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 3, "target": 5},
            {"source": 4, "target": 5},
            {"source": 5, "target": 6}
        ]
        
        result = topological_sort_nodes(nodes, connections)
        
        assert result.index(1) < result.index(2)
        assert result.index(2) < result.index(3)
        assert result.index(2) < result.index(4)
        assert result.index(3) < result.index(5)
        assert result.index(4) < result.index(5)
        assert result.index(5) < result.index(6)
    
    def test_empty_nodes(self):
        from gui.pages.workflow_page import topological_sort_nodes
        
        result = topological_sort_nodes([], [])
        assert result == []
    
    def test_single_node(self):
        from gui.pages.workflow_page import topological_sort_nodes
        
        nodes = [{"id": 1, "name": "单独节点"}]
        result = topological_sort_nodes(nodes, [])
        assert result == [1]
    
    def test_disconnected_nodes(self):
        from gui.pages.workflow_page import topological_sort_nodes
        
        nodes = [
            {"id": 1, "name": "节点1"},
            {"id": 2, "name": "节点2"},
            {"id": 3, "name": "节点3"}
        ]
        connections = []
        
        result = topological_sort_nodes(nodes, connections)
        
        assert set(result) == {1, 2, 3}
        assert len(result) == 3


class TestWorkflowExecutionDeletion:
    def test_delete_execution(self, db_session):
        from services.workflow_service import WorkflowService
        from models.workflow import Workflow, WorkflowExecution

        workflow = Workflow(name="测试工作流", graph_data={"nodes": [], "connections": []})
        db_session.add(workflow)
        db_session.commit()

        execution = WorkflowExecution(workflow_id=workflow.id, status="success")
        db_session.add(execution)
        db_session.commit()

        service = WorkflowService()
        result = service.delete_execution(execution.id)

        assert result == True
        assert db_session.query(WorkflowExecution).filter(WorkflowExecution.id == execution.id).first() is None

    def test_delete_execution_not_found(self, db_session):
        from services.workflow_service import WorkflowService

        service = WorkflowService()
        result = service.delete_execution(999)

        assert result == False

    def test_delete_executions_batch(self, db_session):
        from services.workflow_service import WorkflowService
        from models.workflow import Workflow, WorkflowExecution

        workflow = Workflow(name="测试工作流", graph_data={"nodes": [], "connections": []})
        db_session.add(workflow)
        db_session.commit()

        executions = []
        for i in range(3):
            exec_obj = WorkflowExecution(workflow_id=workflow.id, status="success")
            db_session.add(exec_obj)
            executions.append(exec_obj)
        db_session.commit()

        exec_ids = [e.id for e in executions]

        service = WorkflowService()
        deleted_count = service.delete_executions(exec_ids)

        assert deleted_count == 3

    def test_delete_executions_batch_partial(self, db_session):
        from services.workflow_service import WorkflowService
        from models.workflow import Workflow, WorkflowExecution

        workflow = Workflow(name="测试工作流", graph_data={"nodes": [], "connections": []})
        db_session.add(workflow)
        db_session.commit()

        executions = []
        for i in range(2):
            exec_obj = WorkflowExecution(workflow_id=workflow.id, status="success")
            db_session.add(exec_obj)
            executions.append(exec_obj)
        db_session.commit()

        exec_ids = [e.id for e in executions]
        exec_ids.append(999)

        service = WorkflowService()
        deleted_count = service.delete_executions(exec_ids)

        assert deleted_count == 2


class TestWorkflowImportExport:
    def test_export_workflow(self, db_session):
        from services.workflow_service import WorkflowService
        from models.workflow import Workflow

        workflow = Workflow(
            name="测试工作流",
            description="测试描述",
            graph_data={
                "nodes": [
                    {"id": 1, "node_type": "start", "name": "开始"},
                    {"id": 2, "node_type": "end", "name": "结束"}
                ],
                "connections": [{"source": 1, "target": 2}]
            }
        )
        db_session.add(workflow)
        db_session.commit()

        service = WorkflowService()
        export_data = service.export_workflow(workflow.id)

        assert export_data is not None
        assert export_data["name"] == "测试工作流"
        assert export_data["description"] == "测试描述"
        assert "graph_data" in export_data
        assert export_data["export_version"] == "1.0"

    def test_export_workflow_not_found(self, db_session):
        from services.workflow_service import WorkflowService

        service = WorkflowService()
        export_data = service.export_workflow(999)

        assert export_data is None

    def test_import_workflow(self, db_session):
        from services.workflow_service import WorkflowService

        import_data = {
            "name": "导入的工作流",
            "description": "导入描述",
            "graph_data": {
                "nodes": [
                    {"id": 1, "node_type": "start", "name": "开始"},
                    {"id": 2, "node_type": "end", "name": "结束"}
                ],
                "connections": [{"source": 1, "target": 2}]
            },
            "export_version": "1.0"
        }

        service = WorkflowService()
        result = service.import_workflow(import_data, user_id=1)

        assert result is not None
        assert result.name == "导入的工作流"

    def test_import_workflow_empty_data(self, db_session):
        from services.workflow_service import WorkflowService

        service = WorkflowService()
        result = service.import_workflow(None)
        assert result is None

    def test_generate_unique_name_no_conflict(self, db_session):
        from services.workflow_service import WorkflowService

        service = WorkflowService()
        result = service._generate_unique_name("测试工作流")

        assert result == "测试工作流"

    def test_generate_unique_name_with_conflict(self, db_session):
        from services.workflow_service import WorkflowService
        from models.workflow import Workflow

        workflow = Workflow(name="测试工作流", graph_data={"nodes": [], "connections": []})
        db_session.add(workflow)
        db_session.commit()

        service = WorkflowService()
        result = service._generate_unique_name("测试工作流")

        assert result == "测试工作流 (1)"

    def test_generate_unique_name_multiple_conflicts(self, db_session):
        from services.workflow_service import WorkflowService
        from models.workflow import Workflow

        db_session.add(Workflow(name="测试工作流", graph_data={"nodes": [], "connections": []}))
        db_session.add(Workflow(name="测试工作流 (1)", graph_data={"nodes": [], "connections": []}))
        db_session.add(Workflow(name="测试工作流 (2)", graph_data={"nodes": [], "connections": []}))
        db_session.commit()

        service = WorkflowService()
        result = service._generate_unique_name("测试工作流")

        assert result == "测试工作流 (3)"


class TestWorkflowConcurrency:
    """工作流并发执行测试类"""
    
    def test_multiple_parallel_branches(self):
        """测试多分支并行执行"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "delay", "name": "分支1", "config": {"delay_seconds": 0}},
            {"id": 4, "node_type": "delay", "name": "分支2", "config": {"delay_seconds": 0}},
            {"id": 5, "node_type": "delay", "name": "分支3", "config": {"delay_seconds": 0}},
            {"id": 6, "node_type": "merge", "name": "合并"},
            {"id": 7, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 2, "target": 5},
            {"source": 3, "target": 6},
            {"source": 4, "target": 6},
            {"source": 5, "target": 6},
            {"source": 6, "target": 7}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute(max_workers=4)

        assert result["status"] == "success"
        assert result["success_count"] == 7
        assert result["failed_count"] == 0

    def test_parallel_execution_timing(self):
        """测试并行执行时间正确性"""
        import time
        
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "delay", "name": "延时1", "config": {"delay_seconds": 1}},
            {"id": 4, "node_type": "delay", "name": "延时2", "config": {"delay_seconds": 1}},
            {"id": 5, "node_type": "delay", "name": "延时3", "config": {"delay_seconds": 1}},
            {"id": 6, "node_type": "merge", "name": "合并"},
            {"id": 7, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 2, "target": 5},
            {"source": 3, "target": 6},
            {"source": 4, "target": 6},
            {"source": 5, "target": 6},
            {"source": 6, "target": 7}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        
        start_time = time.time()
        result = executor.execute(max_workers=4)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        assert result["status"] == "success"
        assert execution_time < 3.0, f"并行执行时间应小于3秒，实际为{execution_time:.2f}秒"

    def test_nested_parallel_execution(self):
        """测试嵌套并行执行"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "外层并行"},
            {"id": 3, "node_type": "delay", "name": "分支A", "config": {"delay_seconds": 0}},
            {"id": 4, "node_type": "parallel", "name": "内层并行"},
            {"id": 5, "node_type": "delay", "name": "分支B-1", "config": {"delay_seconds": 0}},
            {"id": 6, "node_type": "delay", "name": "分支B-2", "config": {"delay_seconds": 0}},
            {"id": 7, "node_type": "merge", "name": "内层合并"},
            {"id": 8, "node_type": "merge", "name": "外层合并"},
            {"id": 9, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 4, "target": 5},
            {"source": 4, "target": 6},
            {"source": 5, "target": 7},
            {"source": 6, "target": 7},
            {"source": 3, "target": 8},
            {"source": 7, "target": 8},
            {"source": 8, "target": 9}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute(max_workers=4)

        assert result["status"] == "success"
        assert result["success_count"] == 9

    def test_parallel_with_command_nodes(self):
        """测试并行执行命令节点"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "command", "name": "命令1", "config": {"command": "echo test1", "timeout": 10}},
            {"id": 4, "node_type": "command", "name": "命令2", "config": {"command": "echo test2", "timeout": 10}},
            {"id": 5, "node_type": "command", "name": "命令3", "config": {"command": "echo test3", "timeout": 10}},
            {"id": 6, "node_type": "merge", "name": "合并"},
            {"id": 7, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 2, "target": 5},
            {"source": 3, "target": 6},
            {"source": 4, "target": 6},
            {"source": 5, "target": 6},
            {"source": 6, "target": 7}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute(max_workers=4)

        assert result["status"] == "success"
        assert result["success_count"] == 7
        
        assert "test1" in result["node_results"][3]["output"]
        assert "test2" in result["node_results"][4]["output"]
        assert "test3" in result["node_results"][5]["output"]

    def test_parallel_execution_with_failure(self):
        """测试并行执行时部分节点失败"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "command", "name": "成功命令", "config": {"command": "echo success", "timeout": 10}},
            {"id": 4, "node_type": "command", "name": "失败命令", "config": {"command": "exit 1", "timeout": 10}},
            {"id": 5, "node_type": "delay", "name": "延时节点", "config": {"delay_seconds": 0}},
            {"id": 6, "node_type": "merge", "name": "合并"},
            {"id": 7, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 2, "target": 5},
            {"source": 3, "target": 6},
            {"source": 4, "target": 6},
            {"source": 5, "target": 6},
            {"source": 6, "target": 7}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute(max_workers=4)

        assert result["status"] == "failed"
        assert result["failed_count"] == 1
        assert result["success_count"] == 4

    def test_max_workers_limit(self):
        """测试最大工作线程数限制"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "delay", "name": "延时1", "config": {"delay_seconds": 0}},
            {"id": 4, "node_type": "delay", "name": "延时2", "config": {"delay_seconds": 0}},
            {"id": 5, "node_type": "delay", "name": "延时3", "config": {"delay_seconds": 0}},
            {"id": 6, "node_type": "delay", "name": "延时4", "config": {"delay_seconds": 0}},
            {"id": 7, "node_type": "delay", "name": "延时5", "config": {"delay_seconds": 0}},
            {"id": 8, "node_type": "merge", "name": "合并"},
            {"id": 9, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 2, "target": 5},
            {"source": 2, "target": 6},
            {"source": 2, "target": 7},
            {"source": 3, "target": 8},
            {"source": 4, "target": 8},
            {"source": 5, "target": 8},
            {"source": 6, "target": 8},
            {"source": 7, "target": 8},
            {"source": 8, "target": 9}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute(max_workers=2)

        assert result["status"] == "success"
        assert result["success_count"] == 9

    def test_parallel_execution_order(self):
        """测试并行执行后节点执行顺序正确"""
        execution_order = []
        
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "command", "name": "命令A", "config": {"command": "echo A", "timeout": 10}},
            {"id": 4, "node_type": "command", "name": "命令B", "config": {"command": "echo B", "timeout": 10}},
            {"id": 5, "node_type": "merge", "name": "合并"},
            {"id": 6, "node_type": "command", "name": "命令C", "config": {"command": "echo C", "timeout": 10}},
            {"id": 7, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 3, "target": 5},
            {"source": 4, "target": 5},
            {"source": 5, "target": 6},
            {"source": 6, "target": 7}
        ]

        def track_execution(update):
            node_id = update.get("node_id")
            status = update.get("status")
            if status == "running":
                execution_order.append(node_id)

        executor = WorkflowExecutor(1, nodes, connections)
        executor.set_callbacks(track_execution, None)
        result = executor.execute(max_workers=4)

        assert result["status"] == "success"
        
        start_idx = execution_order.index(1)
        parallel_idx = execution_order.index(2)
        
        assert start_idx < parallel_idx
        
        merge_idx = execution_order.index(5)
        cmd_a_idx = execution_order.index(3)
        cmd_b_idx = execution_order.index(4)
        
        assert parallel_idx < cmd_a_idx
        assert parallel_idx < cmd_b_idx
        assert cmd_a_idx < merge_idx
        assert cmd_b_idx < merge_idx
        
        cmd_c_idx = execution_order.index(6)
        end_idx = execution_order.index(7)
        
        assert merge_idx < cmd_c_idx
        assert cmd_c_idx < end_idx

    def test_concurrent_callback_handling(self):
        """测试并发执行时回调正确处理"""
        updates = []
        logs = []
        
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

        def on_execution(update):
            updates.append(update)

        def on_log(log):
            logs.append(log)

        executor = WorkflowExecutor(1, nodes, connections)
        executor.set_callbacks(on_execution, on_log)
        result = executor.execute(max_workers=4)

        assert result["status"] == "success"
        
        success_updates = [u for u in updates if u.get("status") == "success"]
        assert len(success_updates) == 6
        
        assert len(logs) > 0

    def test_parallel_with_script_nodes(self):
        """测试并行执行脚本节点"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行"},
            {"id": 3, "node_type": "script", "name": "脚本1", "config": {
                "script_content": "echo script1",
                "script_language": "bash",
                "timeout": 10
            }},
            {"id": 4, "node_type": "script", "name": "脚本2", "config": {
                "script_content": "print('script2')",
                "script_language": "python",
                "timeout": 10
            }},
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
        assert result["success_count"] == 6
        
        assert "script1" in result["node_results"][3]["output"]
        assert "script2" in result["node_results"][4]["output"]

    def test_complex_parallel_workflow(self):
        """测试复杂并行工作流"""
        nodes = [
            {"id": 1, "node_type": "start", "name": "开始"},
            {"id": 2, "node_type": "parallel", "name": "并行1"},
            {"id": 3, "node_type": "command", "name": "命令A", "config": {"command": "echo A", "timeout": 10}},
            {"id": 4, "node_type": "parallel", "name": "并行2"},
            {"id": 5, "node_type": "command", "name": "命令B1", "config": {"command": "echo B1", "timeout": 10}},
            {"id": 6, "node_type": "command", "name": "命令B2", "config": {"command": "echo B2", "timeout": 10}},
            {"id": 7, "node_type": "merge", "name": "合并2"},
            {"id": 8, "node_type": "merge", "name": "合并1"},
            {"id": 9, "node_type": "command", "name": "命令C", "config": {"command": "echo C", "timeout": 10}},
            {"id": 10, "node_type": "end", "name": "结束"}
        ]
        connections = [
            {"source": 1, "target": 2},
            {"source": 2, "target": 3},
            {"source": 2, "target": 4},
            {"source": 4, "target": 5},
            {"source": 4, "target": 6},
            {"source": 5, "target": 7},
            {"source": 6, "target": 7},
            {"source": 3, "target": 8},
            {"source": 7, "target": 8},
            {"source": 8, "target": 9},
            {"source": 9, "target": 10}
        ]

        executor = WorkflowExecutor(1, nodes, connections)
        result = executor.execute(max_workers=4)

        assert result["status"] == "success"
        assert result["success_count"] == 10
