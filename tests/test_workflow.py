import pytest
from unittest.mock import Mock, patch, MagicMock
from core.node_types import (
    BaseNode, StartNode, EndNode, ScriptNode, DelayNode,
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

    def test_script_node_success(self):
        node = ScriptNode(1, "脚本节点", config={"command": "echo hello", "timeout": 10})
        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert "hello" in result.output

    def test_script_node_failure(self):
        node = ScriptNode(1, "脚本节点", config={"command": "exit 1", "timeout": 10})
        result = node.execute()
        assert result.status == NodeStatus.FAILED

    def test_get_node_class(self):
        assert get_node_class("start") == StartNode
        assert get_node_class("end") == EndNode
        assert get_node_class("script") == ScriptNode
        assert get_node_class("unknown") == BaseNode

    def test_get_all_node_types(self):
        all_types = get_all_node_types()
        assert "start" in all_types
        assert "end" in all_types
        assert "script" in all_types
        assert "delay" in all_types
        assert "condition" in all_types

        start_info = all_types["start"]
        assert start_info["display_name"] == "开始"
        assert start_info["category"] == "control"


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
            {"id": 2, "node_type": "script", "name": "脚本", "config": {"command": "echo test", "timeout": 10}},
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
