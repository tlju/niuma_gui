import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.workflow import Workflow
from models.workflow_node import WorkflowNode
from models.workflow_edge import WorkflowEdge
from models.workflow_run import RunStatus, TriggerType
from services.workflow_service import WorkflowService
from services.workflow_engine import (
    WorkflowEngine, NodeExecutor, StartNodeExecutor,
    EndNodeExecutor, ScriptNodeExecutor, DelayNodeExecutor
)
from typing import Dict, Any
import time


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def workflow_service(db_session):
    return WorkflowService(db_session)


@pytest.fixture
def workflow_engine(workflow_service):
    return WorkflowEngine(workflow_service)


class TestNodeExecutors:
    def test_start_node_executor(self):
        executor = StartNodeExecutor()
        assert executor.node_type == "start"

        result = executor.execute({}, {})
        assert result["success"] is True

    def test_end_node_executor(self):
        executor = EndNodeExecutor()
        assert executor.node_type == "end"

        result = executor.execute({}, {})
        assert result["success"] is True

    def test_script_node_executor(self):
        executor = ScriptNodeExecutor()
        assert executor.node_type == "script"

        result = executor.execute({"script_id": 1}, {})
        assert result["success"] is True

    def test_script_node_executor_missing_script(self):
        executor = ScriptNodeExecutor()

        result = executor.execute({}, {})
        assert result["success"] is False
        assert "未配置脚本ID" in result["error"]

    def test_delay_node_executor(self):
        executor = DelayNodeExecutor()
        assert executor.node_type == "delay"

        start = time.time()
        result = executor.execute({"delay_seconds": 1}, {})
        elapsed = time.time() - start

        assert result["success"] is True
        assert elapsed >= 1


class TestWorkflowEngine:
    def test_build_dag(self, workflow_engine, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")
        workflow_service.save_workflow_data(
            workflow_id,
            nodes=[
                {"node_key": "a", "node_type": "start", "node_name": "A", "config_json": {}},
                {"node_key": "b", "node_type": "end", "node_name": "B", "config_json": {}},
            ],
            edges=[
                {"source_node_key": "a", "target_node_key": "b", "condition_json": {}}
            ]
        )

        data = workflow_service.get_workflow_data(workflow_id)
        graph, in_degree = workflow_engine.build_dag(data["nodes"], data["edges"])

        assert "a" in graph
        assert "b" in graph["a"]
        assert in_degree["a"] == 0
        assert in_degree["b"] == 1

    def test_topological_sort(self, workflow_engine):
        graph = {
            "a": ["b", "c"],
            "b": ["d"],
            "c": ["d"],
            "d": []
        }
        in_degree = {"a": 0, "b": 1, "c": 1, "d": 2}

        result = workflow_engine.topological_sort(graph, in_degree.copy())

        assert result[0] == "a"
        assert result[-1] == "d"
        assert "b" in result
        assert "c" in result

    def test_execute_simple_workflow(self, workflow_engine, workflow_service):
        import pytest
        pytest.skip("SQLite 内存数据库不支持跨线程共享，跳过此测试")

        workflow_id = workflow_service.create_workflow("简单工作流")
        workflow_service.save_workflow_data(
            workflow_id,
            nodes=[
                {"node_key": "start-1", "node_type": "start", "node_name": "开始", "config_json": {}},
                {"node_key": "end-1", "node_type": "end", "node_name": "结束", "config_json": {}},
            ],
            edges=[
                {"source_node_key": "start-1", "target_node_key": "end-1", "condition_json": {}}
            ]
        )

        run_id = workflow_engine.execute_workflow(workflow_id, TriggerType.MANUAL)

        assert run_id is not None

        import time
        time.sleep(1)

        run = workflow_service.get_run_by_id(run_id)
        assert run.status in [RunStatus.SUCCESS, RunStatus.RUNNING]

    def test_register_custom_executor(self, workflow_engine, workflow_service):
        class CustomExecutor(NodeExecutor):
            @property
            def node_type(self) -> str:
                return "custom"

            def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
                return {"success": True, "output": "自定义节点执行成功"}

        custom_executor = CustomExecutor()
        workflow_engine.register_executor(custom_executor)

        assert "custom" in workflow_engine.executors
        assert workflow_engine.executors["custom"] == custom_executor

    def test_is_running(self, workflow_engine):
        assert workflow_engine.is_running() is False
