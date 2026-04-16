import pytest
from PyQt6.QtWidgets import QApplication
from gui.workflow_canvas import WorkflowCanvas
from unittest.mock import Mock


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestWorkflowCanvasExecuteMode:
    def test_execute_mode_allows_adding_nodes(self, app):
        canvas = WorkflowCanvas(mode="execute")
        
        assert canvas._read_only == True
        
        node = canvas.add_node("start", 100, 100, name="开始节点", node_id=1)
        
        assert node is not None
        assert len(canvas.nodes) == 1
        assert 1 in canvas.nodes
        
    def test_execute_mode_allows_adding_connections(self, app):
        canvas = WorkflowCanvas(mode="execute")
        
        node1 = canvas.add_node("start", 100, 100, name="开始", node_id=1)
        node2 = canvas.add_node("end", 300, 100, name="结束", node_id=2)
        
        connection = canvas.add_connection(1, 2)
        
        assert connection is not None
        assert len(canvas.connections) == 1
        
    def test_execute_mode_nodes_not_movable(self, app):
        canvas = WorkflowCanvas(mode="execute")
        
        node = canvas.add_node("start", 100, 100, name="开始节点", node_id=1)
        
        from PyQt6.QtWidgets import QGraphicsItem
        flags = node.flags()
        movable_flag = QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        
        assert not (flags & movable_flag)
        
    def test_edit_mode_nodes_movable(self, app):
        canvas = WorkflowCanvas(mode="edit")
        
        node = canvas.add_node("start", 100, 100, name="开始节点", node_id=1)
        
        from PyQt6.QtWidgets import QGraphicsItem
        movable_flag = node.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        
        assert movable_flag != 0
        
    def test_execute_mode_load_graph_data(self, app):
        canvas = WorkflowCanvas(mode="execute")
        
        graph_data = {
            "nodes": [
                {"id": 1, "node_type": "start", "name": "开始", "x": 100, "y": 100},
                {"id": 2, "node_type": "end", "name": "结束", "x": 300, "y": 100}
            ],
            "connections": [
                {"source": 1, "target": 2}
            ]
        }
        
        canvas.load_graph_data(graph_data)
        
        assert len(canvas.nodes) == 2
        assert len(canvas.connections) == 1
        assert 1 in canvas.nodes
        assert 2 in canvas.nodes
        
    def test_execute_mode_prevents_modification(self, app):
        canvas = WorkflowCanvas(mode="execute")
        
        node = canvas.add_node("start", 100, 100, name="开始节点", node_id=1)
        
        canvas.remove_node(1)
        
        assert len(canvas.nodes) == 1
        assert 1 in canvas.nodes
