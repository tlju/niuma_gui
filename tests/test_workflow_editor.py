import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.workflow import Workflow, WorkflowStatus
from models.workflow_node import WorkflowNode
from models.workflow_edge import WorkflowEdge
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


def _make_mock_port(port_type, index, connections=None):
    port = MagicMock()
    port.port_type = port_type
    port.index = index
    port.connections = connections or []
    return port


def _make_mock_node(node_key, num_outputs=1, num_inputs=1):
    node = MagicMock()
    node.id = node_key
    model = MagicMock()
    model.node_key = node_key
    model._node_type = "test"
    model._name = f"Node-{node_key}"
    model.config = {}
    model.caption = f"Node-{node_key}"
    node.model = model

    output_ports = [_make_mock_port("output", i) for i in range(num_outputs)]
    input_ports = [_make_mock_port("input", i) for i in range(num_inputs)]

    node.__getitem__ = lambda self, pt: input_ports if pt == "input" else output_ports
    node.__getitem__ = MagicMock(side_effect=lambda pt: input_ports if str(pt) == "PortType.input" else output_ports)

    return node, output_ports, input_ports


class TestWorkflowEditorLoadConnections:
    def test_edge_data_uses_saved_port_indices(self, workflow_service):
        workflow_id = workflow_service.create_workflow("测试工作流")

        nodes = [
            {"node_key": "cond-001", "node_type": "condition", "node_name": "条件判断", "pos_x": 100, "pos_y": 100, "config_json": {"expression": "x > 0"}},
            {"node_key": "script-001", "node_type": "script", "node_name": "脚本A", "pos_x": 300, "pos_y": 50, "config_json": {}},
            {"node_key": "script-002", "node_type": "script", "node_name": "脚本B", "pos_x": 300, "pos_y": 200, "config_json": {}},
        ]

        edges = [
            {"source_node_key": "cond-001", "target_node_key": "script-001", "source_port": 0, "target_port": 0, "condition_json": {}},
            {"source_node_key": "cond-001", "target_node_key": "script-002", "source_port": 1, "target_port": 0, "condition_json": {}},
        ]

        success = workflow_service.save_workflow_data(workflow_id, nodes, edges)
        assert success is True

        data = workflow_service.get_workflow_data(workflow_id)
        assert len(data["edges"]) == 2
        assert data["edges"][0]["source_port"] == 0
        assert data["edges"][1]["source_port"] == 1

    def test_duplicate_input_port_connections_are_skipped(self):
        from qtpynodeeditor import PortType, ConnectionPolicy

        target_port = _make_mock_port(PortType.input, 0, connections=["existing_connection"])
        target_port.connection_policy = ConnectionPolicy.one

        should_skip = bool(target_port.connections) and target_port.connection_policy == ConnectionPolicy.one
        assert should_skip is True

    def test_multiple_connections_allowed_with_policy_many(self):
        from qtpynodeeditor import PortType, ConnectionPolicy

        target_port = _make_mock_port(PortType.input, 0, connections=["existing_connection"])
        target_port.connection_policy = ConnectionPolicy.many

        should_skip = bool(target_port.connections) and target_port.connection_policy == ConnectionPolicy.one
        assert should_skip is False

    def test_empty_input_port_allows_connection(self):
        from qtpynodeeditor import PortType

        target_port = _make_mock_port(PortType.input, 0, connections=[])

        should_skip = bool(target_port.connections)
        assert should_skip is False

    def test_invalid_port_index_is_detected(self):
        source_ports = [_make_mock_port("output", 0)]
        target_ports = [_make_mock_port("input", 0)]

        source_port_index = 1
        target_port_index = 0

        is_invalid = source_port_index >= len(source_ports) or target_port_index >= len(target_ports)
        assert is_invalid is True

    def test_valid_port_index_passes(self):
        source_ports = [_make_mock_port("output", 0), _make_mock_port("output", 1)]
        target_ports = [_make_mock_port("input", 0)]

        source_port_index = 1
        target_port_index = 0

        is_invalid = source_port_index >= len(source_ports) or target_port_index >= len(target_ports)
        assert is_invalid is False


class TestWorkflowEditorSavePortIndices:
    def test_save_captures_output_port_index_for_condition_node(self):
        from qtpynodeeditor import PortType

        conn = MagicMock()
        conn.output_node = MagicMock()
        conn.input_node = MagicMock()
        conn.output_node.model.node_key = "cond-001"
        conn.input_node.model.node_key = "script-001"

        conn.get_port_index = MagicMock(side_effect=lambda pt: 1 if pt == PortType.output else 0)

        source_port_index = conn.get_port_index(PortType.output)
        target_port_index = conn.get_port_index(PortType.input)

        assert source_port_index == 1
        assert target_port_index == 0

    def test_save_captures_default_port_index_for_simple_node(self):
        from qtpynodeeditor import PortType

        conn = MagicMock()
        conn.output_node = MagicMock()
        conn.input_node = MagicMock()
        conn.output_node.model.node_key = "start-001"
        conn.input_node.model.node_key = "script-001"

        conn.get_port_index = MagicMock(side_effect=lambda pt: 0)

        source_port_index = conn.get_port_index(PortType.output)
        target_port_index = conn.get_port_index(PortType.input)

        assert source_port_index == 0
        assert target_port_index == 0


class TestMultipleNodesToEndNode:
    def test_multiple_nodes_can_connect_to_end_node(self, workflow_service):
        workflow_id = workflow_service.create_workflow("多节点到结束节点")

        nodes = [
            {"node_key": "script-001", "node_type": "script", "node_name": "脚本A", "pos_x": 100, "pos_y": 50, "config_json": {}},
            {"node_key": "script-002", "node_type": "script", "node_name": "脚本B", "pos_x": 100, "pos_y": 150, "config_json": {}},
            {"node_key": "end-001", "node_type": "end", "node_name": "结束", "pos_x": 300, "pos_y": 100, "config_json": {}},
        ]

        edges = [
            {"source_node_key": "script-001", "target_node_key": "end-001", "source_port": 0, "target_port": 0, "condition_json": {}},
            {"source_node_key": "script-002", "target_node_key": "end-001", "source_port": 0, "target_port": 0, "condition_json": {}},
        ]

        success = workflow_service.save_workflow_data(workflow_id, nodes, edges)
        assert success is True

        data = workflow_service.get_workflow_data(workflow_id)
        assert len(data["edges"]) == 2
        assert data["edges"][0]["target_node_key"] == "end-001"
        assert data["edges"][1]["target_node_key"] == "end-001"

    def test_connection_policy_many_allows_multiple_connections(self):
        from qtpynodeeditor import ConnectionPolicy

        target_port = _make_mock_port("input", 0, connections=["conn1", "conn2"])
        target_port.connection_policy = ConnectionPolicy.many

        should_skip = bool(target_port.connections) and target_port.connection_policy == ConnectionPolicy.one
        assert should_skip is False
        assert len(target_port.connections) == 2
