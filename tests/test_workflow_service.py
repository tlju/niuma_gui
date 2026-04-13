import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.workflow import Workflow, WorkflowStatus
from models.workflow_node import WorkflowNode
from models.workflow_edge import WorkflowEdge
from models.workflow_run import WorkflowRun, RunStatus, TriggerType
from models.workflow_run_node import WorkflowRunNode
from services.workflow_service import WorkflowService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def workflow_service(db_session):
    return WorkflowService(db_session)


class TestWorkflowService:
    def test_create_workflow(self, workflow_service):
        workflow_id = workflow_service.create_workflow(
            name="测试工作流",
            description="这是一个测试工作流"
        )
        assert workflow_id is not None
        assert workflow_id > 0

    def test_get_all_workflows(self, workflow_service):
        workflow_service.create_workflow("工作流1")
        workflow_service.create_workflow("工作流2")

        workflows = workflow_service.get_all_workflows()
        assert len(workflows) == 2

    def test_get_workflow_by_id(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")

        workflow = workflow_service.get_workflow_by_id(workflow_id)
        assert workflow is not None
        assert workflow.name == "测试工作流"

    def test_update_workflow(self, workflow_service):
        workflow_id = workflow_service.create_workflow("原始名称")

        success = workflow_service.update_workflow(
            workflow_id,
            name="新名称",
            description="新描述",
            status=WorkflowStatus.PUBLISHED
        )
        assert success is True

        workflow = workflow_service.get_workflow_by_id(workflow_id)
        assert workflow.name == "新名称"
        assert workflow.description == "新描述"
        assert workflow.status == WorkflowStatus.PUBLISHED

    def test_delete_workflow(self, workflow_service):
        workflow_id = workflow_service.create_workflow("待删除工作流")

        success = workflow_service.delete_workflow(workflow_id)
        assert success is True

        workflow = workflow_service.get_workflow_by_id(workflow_id)
        assert workflow is None

    def test_save_workflow_data(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")

        nodes = [
            {
                "node_key": "start-001",
                "node_type": "start",
                "node_name": "开始",
                "pos_x": 100,
                "pos_y": 100,
                "config_json": {}
            },
            {
                "node_key": "end-001",
                "node_type": "end",
                "node_name": "结束",
                "pos_x": 300,
                "pos_y": 100,
                "config_json": {}
            }
        ]

        edges = [
            {
                "source_node_key": "start-001",
                "target_node_key": "end-001",
                "source_port": 0,
                "target_port": 0,
                "condition_json": {}
            }
        ]

        success = workflow_service.save_workflow_data(workflow_id, nodes, edges)
        assert success is True

        data = workflow_service.get_workflow_data(workflow_id)
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_create_run(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")
        run_id = workflow_service.create_run(workflow_id, TriggerType.MANUAL)

        assert run_id is not None
        assert run_id > 0

    def test_get_runs_by_workflow(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")

        workflow_service.create_run(workflow_id, TriggerType.MANUAL)
        workflow_service.create_run(workflow_id, TriggerType.MANUAL)

        runs = workflow_service.get_runs_by_workflow(workflow_id)
        assert len(runs) == 2

    def test_update_run_status(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")
        run_id = workflow_service.create_run(workflow_id)

        from datetime import datetime
        success = workflow_service.update_run_status(
            run_id,
            RunStatus.RUNNING,
            start_time=datetime.now()
        )
        assert success is True

        run = workflow_service.get_run_by_id(run_id)
        assert run.status == RunStatus.RUNNING
        assert run.start_time is not None

    def test_create_run_node(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")
        run_id = workflow_service.create_run(workflow_id)

        run_node_id = workflow_service.create_run_node(run_id, "node-001")
        assert run_node_id is not None

    def test_update_run_node(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")
        run_id = workflow_service.create_run(workflow_id)
        run_node_id = workflow_service.create_run_node(run_id, "node-001")

        from datetime import datetime
        success = workflow_service.update_run_node(
            run_node_id,
            status=RunStatus.SUCCESS,
            output="执行成功",
            end_time=datetime.now()
        )
        assert success is True

        run_nodes = workflow_service.get_run_nodes(run_id)
        assert len(run_nodes) == 1
        assert run_nodes[0].status == RunStatus.SUCCESS
        assert run_nodes[0].output == "执行成功"
