from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QApplication, QScrollArea, QDialog, QFormLayout,
    QLineEdit, QSpinBox, QComboBox, QTextEdit, QMessageBox,
    QSplitter, QListWidget, QListWidgetItem, QGroupBox, QDoubleSpinBox,
    QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen, QFont
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from gui.workflow.node_types import (
    NODE_TYPES, get_node_type, get_all_node_types,
    get_node_types_by_category, NodeTypeDefinition
)
from services.workflow_service import WorkflowService
from typing import Dict, List, Any, Optional
import uuid

logger = get_logger(__name__)

try:
    from qtpynodeeditor import (
        NodeData, NodeDataModel, NodeDataType,
        FlowScene, FlowView, DataModelRegistry,
        ConnectionPolicy, PortType, NodeValidationState, Port
    )
    HAS_NODE_EDITOR = True
except ImportError:
    HAS_NODE_EDITOR = False
    NodeData = None
    NodeDataModel = None
    NodeDataType = None
    FlowScene = None
    FlowView = None
    DataModelRegistry = None
    ConnectionPolicy = None
    PortType = None
    NodeValidationState = None
    Port = None
    logger.warning("qtpynodeeditor 未安装，工作流编辑器将使用简化模式")


if HAS_NODE_EDITOR:
    class FlowData(NodeData):
        data_type = NodeDataType("flow", "Flow")

        def __init__(self, data: Any = None):
            self._data = data

        @property
        def data(self):
            return self._data


    class BaseNodeModel(NodeDataModel):
        caption_visible = True
        port_caption_visible = True
        data_type = FlowData.data_type

        def __init__(self, style=None, parent=None):
            super().__init__(style=style, parent=parent)
            self._node_type = "base"
            self._name = "Base"
            self._config: Dict[str, Any] = {}
            self._node_key = str(uuid.uuid4())
            self._validation_state = NodeValidationState.valid
            self._validation_message = ""

        @property
        def node_key(self) -> str:
            return self._node_key

        @node_key.setter
        def node_key(self, value: str):
            self._node_key = value

        @property
        def config(self) -> Dict[str, Any]:
            return self._config

        @config.setter
        def config(self, value: Dict[str, Any]):
            self._config = value

        @property
        def caption(self) -> str:
            return self._name

        def validation_state(self) -> NodeValidationState:
            return self._validation_state

        def validation_message(self) -> str:
            return self._validation_message

        def port_in_connection_policy(self, port_index: int):
            return ConnectionPolicy.many

        def save(self) -> Dict[str, Any]:
            return {
                "node_key": self._node_key,
                "node_type": self._node_type,
                "node_name": self._name,
                "config": self._config
            }

        def restore(self, data: Dict[str, Any]):
            self._node_key = data.get("node_key", str(uuid.uuid4()))
            self._name = data.get("node_name", self._node_type)
            self._config = data.get("config", {})

        def out_data(self, port: int) -> NodeData:
            return FlowData()

        def set_in_data(self, data: NodeData, port: Port):
            pass

        def embedded_widget(self):
            return None


    class StartNodeModel(BaseNodeModel):
        name = "Start"
        num_ports = {
            'input': 0,
            'output': 1,
        }

        def __init__(self, style=None, parent=None):
            super().__init__(style=style, parent=parent)
            self._node_type = "start"
            self._name = "开始"


    class EndNodeModel(BaseNodeModel):
        name = "End"
        num_ports = {
            'input': 1,
            'output': 0,
        }

        def __init__(self, style=None, parent=None):
            super().__init__(style=style, parent=parent)
            self._node_type = "end"
            self._name = "结束"


    class ScriptNodeModel(BaseNodeModel):
        name = "Script"
        num_ports = {
            'input': 1,
            'output': 1,
        }

        def __init__(self, style=None, parent=None):
            super().__init__(style=style, parent=parent)
            self._node_type = "script"
            self._name = "执行脚本"
            self._config = {"script_id": None, "server_id": None}


    class SSHNodeModel(BaseNodeModel):
        name = "SSH"
        num_ports = {
            'input': 1,
            'output': 1,
        }

        def __init__(self, style=None, parent=None):
            super().__init__(style=style, parent=parent)
            self._node_type = "ssh"
            self._name = "SSH命令"
            self._config = {"server_id": None, "command": ""}


    class ConditionNodeModel(BaseNodeModel):
        name = "Condition"
        num_ports = {
            'input': 1,
            'output': 2,
        }
        port_caption = {
            'input': {0: 'Input'},
            'output': {0: 'True', 1: 'False'}
        }
        port_caption_visible = {
            'input': {0: True},
            'output': {0: True, 1: True}
        }
        data_type = FlowData.data_type

        def __init__(self, style=None, parent=None):
            super().__init__(style=style, parent=parent)
            self._node_type = "condition"
            self._name = "条件判断"
            self._config = {"expression": "true"}


    class DelayNodeModel(BaseNodeModel):
        name = "Delay"
        num_ports = {
            'input': 1,
            'output': 1,
        }

        def __init__(self, style=None, parent=None):
            super().__init__(style=style, parent=parent)
            self._node_type = "delay"
            self._name = "延迟"
            self._config = {"delay_seconds": 1}


    NODE_MODEL_CLASSES = {
        "start": StartNodeModel,
        "end": EndNodeModel,
        "script": ScriptNodeModel,
        "ssh": SSHNodeModel,
        "condition": ConditionNodeModel,
        "delay": DelayNodeModel,
    }

    class ArrowConnectionPainter:
        @staticmethod
        def paint(painter, connection, style):
            from qtpynodeeditor.connection_painter import (
                draw_hovered_or_selected, draw_sketch_line, draw_normal_line,
                cubic_path
            )
            from qtpynodeeditor.connection_geometry import ConnectionGeometry

            draw_hovered_or_selected(painter, connection, style)
            draw_sketch_line(painter, connection, style)
            draw_normal_line(painter, connection, style)

            geom = connection.geometry
            source, sink = geom.source, geom.sink

            if connection.requires_port:
                point_diameter = style.point_diameter
                painter.setPen(style.construction_color)
                painter.setBrush(style.construction_color)
                point_radius = point_diameter / 2.0
                painter.drawEllipse(source, point_radius, point_radius)
                painter.drawEllipse(sink, point_radius, point_radius)

            if not connection.requires_port:
                cubic = cubic_path(geom)
                arrow_size = 10

                end_point = sink
                angle = _get_line_angle(cubic, 0.95)

                import math
                arrow_p1 = end_point - QPointF(
                    arrow_size * math.cos(angle - math.pi / 6),
                    arrow_size * math.sin(angle - math.pi / 6)
                )
                arrow_p2 = end_point - QPointF(
                    arrow_size * math.cos(angle + math.pi / 6),
                    arrow_size * math.sin(angle + math.pi / 6)
                )

                color = style.get_normal_color()
                painter.setPen(color)
                painter.setBrush(color)
                from PyQt6.QtGui import QPolygonF
                arrow = QPolygonF([end_point, arrow_p1, arrow_p2])
                painter.drawPolygon(arrow)

        @staticmethod
        def get_painter_stroke(geom):
            from PyQt6.QtGui import QPainterPath, QPainterPathStroker
            from qtpynodeeditor.connection_painter import cubic_path

            cubic = cubic_path(geom)
            source = geom.source
            sink = geom.sink
            result = QPainterPath(source)
            segments = 20

            for i in range(segments):
                ratio = float(i + 1) / segments
                result.lineTo(cubic.pointAtPercent(ratio))

            arrow_size = 10
            angle = _get_line_angle(cubic, 0.95)
            import math
            arrow_p1 = sink - QPointF(
                arrow_size * math.cos(angle - math.pi / 6),
                arrow_size * math.sin(angle - math.pi / 6)
            )
            arrow_p2 = sink - QPointF(
                arrow_size * math.cos(angle + math.pi / 6),
                arrow_size * math.sin(angle + math.pi / 6)
            )
            result.lineTo(arrow_p1)
            result.moveTo(sink)
            result.lineTo(arrow_p2)

            stroker = QPainterPathStroker()
            stroker.setWidth(10.0)
            return stroker.createStroke(result)

    def _get_line_angle(path, percent):
        import math
        p1 = path.pointAtPercent(percent - 0.01)
        p2 = path.pointAtPercent(percent)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.atan2(dy, dx)
else:
    NODE_MODEL_CLASSES = {}


def create_node_registry():
    if not HAS_NODE_EDITOR:
        return None

    registry = DataModelRegistry()

    registry.register_model(StartNodeModel, category="控制")
    registry.register_model(EndNodeModel, category="控制")
    registry.register_model(ScriptNodeModel, category="操作")
    registry.register_model(SSHNodeModel, category="操作")
    registry.register_model(ConditionNodeModel, category="控制")
    registry.register_model(DelayNodeModel, category="控制")

    return registry


class NodeConfigDialog(QDialog):
    def __init__(self, node_type: str, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.node_type = node_type
        self.config = config.copy()
        self.setWindowTitle(f"配置节点: {node_type}")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        node_def = get_node_type(self.node_type)
        if not node_def:
            layout.addWidget(QLabel("未知节点类型"))
            return

        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setText(node_def.display_name)
        form_layout.addRow("节点名称:", self.name_edit)

        self.config_widgets = {}
        for key, schema in node_def.config_schema.items():
            widget_type = schema.get("type", "string")

            if widget_type == "integer":
                widget = QSpinBox()
                widget.setMinimum(schema.get("min", 0))
                widget.setMaximum(schema.get("max", 999999))
                if key in self.config and self.config[key] is not None:
                    widget.setValue(self.config[key])
            elif widget_type == "text":
                widget = QTextEdit()
                widget.setMaximumHeight(100)
                if key in self.config and self.config[key]:
                    widget.setPlainText(str(self.config[key]))
            else:
                widget = QLineEdit()
                if key in self.config and self.config[key] is not None:
                    widget.setText(str(self.config[key]))

            form_layout.addRow(schema.get("label", key) + ":", widget)
            self.config_widgets[key] = widget

        form_group = QGroupBox("节点配置")
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_config(self) -> Dict[str, Any]:
        result = {}

        node_def = get_node_type(self.node_type)
        if node_def:
            for key, schema in node_def.config_schema.items():
                widget = self.config_widgets.get(key)
                if widget:
                    widget_type = schema.get("type", "string")
                    if widget_type == "integer":
                        result[key] = widget.value()
                    elif widget_type == "text":
                        result[key] = widget.toPlainText()
                    else:
                        text = widget.text().strip()
                        if text:
                            try:
                                result[key] = int(text)
                            except ValueError:
                                result[key] = text

        return result

    def get_name(self) -> str:
        return self.name_edit.text().strip()


class WorkflowEditorPage(QWidget):
    workflow_saved = pyqtSignal()
    workflow_executed = pyqtSignal(int)

    def __init__(
        self,
        workflow_service: WorkflowService,
        workflow_id: Optional[int] = None,
        parent=None
    ):
        super().__init__(parent)
        self.workflow_service = workflow_service
        self.workflow_id = workflow_id
        self._scene = None
        self._view = None
        self._registry = None
        self._nodes: Dict[str, Any] = {}
        self._is_modified = False

        self.init_ui()

        if workflow_id:
            self.load_workflow(workflow_id)

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "workflow_page"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        palette_widget = self._create_node_palette()
        splitter.addWidget(palette_widget)

        editor_widget = self._create_editor()
        splitter.addWidget(editor_widget)

        splitter.setSizes([200, 800])

        layout.addWidget(splitter)

    def _create_toolbar(self) -> QFrame:
        toolbar = QFrame()
        toolbar.setProperty("class", "toolbar")
        toolbar.setMaximumHeight(50)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.save_btn = QPushButton("  保存")
        self.save_btn.setIcon(icons.save_icon())
        self.save_btn.setMinimumHeight(34)
        self.save_btn.clicked.connect(self.save_workflow)
        layout.addWidget(self.save_btn)

        self.run_btn = QPushButton("  执行")
        self.run_btn.setIcon(icons.run_icon())
        self.run_btn.setMinimumHeight(34)
        self.run_btn.setProperty("class", "success")
        self.run_btn.clicked.connect(self.execute_workflow)
        layout.addWidget(self.run_btn)

        layout.addStretch()

        self.title_label = QLabel("新建工作流")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)

        return toolbar

    def _create_node_palette(self) -> QWidget:
        palette = QFrame()
        palette.setFrameShape(QFrame.Shape.StyledPanel)
        palette.setMaximumWidth(250)
        layout = QVBoxLayout(palette)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("节点类型")
        title.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        categories_widget = QWidget()
        categories_layout = QVBoxLayout(categories_widget)
        categories_layout.setContentsMargins(0, 0, 0, 0)
        categories_layout.setSpacing(5)

        categories = get_node_types_by_category()
        for category, node_types in categories.items():
            group = QGroupBox(category)
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(5, 5, 5, 5)
            group_layout.setSpacing(3)

            for node_type in node_types:
                item = QPushButton(node_type.display_name)
                item.setProperty("class", "node-item")
                item.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {node_type.color};
                        color: white;
                        border: none;
                        padding: 8px;
                        text-align: left;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        opacity: 0.8;
                    }}
                """)
                item.clicked.connect(
                    lambda checked, t=node_type.type_id: self._add_node(t)
                )
                group_layout.addWidget(item)

            categories_layout.addWidget(group)

        categories_layout.addStretch()
        scroll.setWidget(categories_widget)
        layout.addWidget(scroll)

        return palette

    def _create_editor(self) -> QWidget:
        editor = QFrame()
        editor.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_NODE_EDITOR:
            self._registry = create_node_registry()
            self._scene = FlowScene(self._registry)
            self._view = FlowView(self._scene)
            self._view.mouseDoubleClickEvent = self._on_double_click
            self._view.keyPressEvent = self._on_key_press

            import qtpynodeeditor.connection_painter as cp
            cp.ConnectionPainter.paint = ArrowConnectionPainter.paint
            cp.ConnectionPainter.get_painter_stroke = ArrowConnectionPainter.get_painter_stroke

            import qtpynodeeditor.connection_graphics_object as cgo
            original_conn_mouse_press = cgo.ConnectionGraphicsObject.mousePressEvent
            original_conn_mouse_move = cgo.ConnectionGraphicsObject.mouseMoveEvent
            original_conn_mouse_release = cgo.ConnectionGraphicsObject.mouseReleaseEvent

            def custom_conn_mouse_press(self, event):
                from PyQt6.QtCore import Qt, QPointF
                from qtpynodeeditor import PortType
                from qtpynodeeditor.node_connection_interaction import NodeConnectionInteraction
                import math

                if self._connection.requires_port:
                    original_conn_mouse_press(self, event)
                    return

                if event.button() != Qt.MouseButton.LeftButton:
                    event.accept()
                    return

                event.accept()

                geom = self._connection.geometry
                click_pos = event.pos()

                out_pos = geom.source
                in_pos = geom.sink

                dist_to_out = math.sqrt(
                    (click_pos.x() - out_pos.x()) ** 2 +
                    (click_pos.y() - out_pos.y()) ** 2
                )
                dist_to_in = math.sqrt(
                    (click_pos.x() - in_pos.x()) ** 2 +
                    (click_pos.y() - in_pos.y()) ** 2
                )

                port_to_disconnect = PortType.input if dist_to_in < dist_to_out else PortType.output

                node = self._connection.get_node(port_to_disconnect)
                if node:
                    interaction = NodeConnectionInteraction(node, self._connection, self._scene)
                    interaction.disconnect(port_to_disconnect)

                self.grabMouse()

            def custom_conn_mouse_move(self, event):
                original_conn_mouse_move(self, event)

            def custom_conn_mouse_release(self, event):
                from qtpynodeeditor.node_connection_interaction import NodeConnectionInteraction

                self.ungrabMouse()
                event.accept()

                if not self._connection.requires_port:
                    return

                node = self._scene.locate_node_at(
                    event.scenePos(),
                    self._scene.views()[0].transform()
                )

                if node:
                    interaction = NodeConnectionInteraction(node, self._connection, self._scene)
                    if interaction.try_connect():
                        node.reset_reaction_to_connection()
                        self._scene.connection_created.emit(self._connection)
                        return

                if self._connection.requires_port:
                    self._scene.delete_connection(self._connection)

            cgo.ConnectionGraphicsObject.mousePressEvent = custom_conn_mouse_press
            cgo.ConnectionGraphicsObject.mouseMoveEvent = custom_conn_mouse_move
            cgo.ConnectionGraphicsObject.mouseReleaseEvent = custom_conn_mouse_release

            import qtpynodeeditor.node_graphics_object as ngo
            original_node_mouse_press = ngo.NodeGraphicsObject.mousePressEvent
            def custom_node_mouse_press(self, event):
                from PyQt6.QtCore import Qt, QPoint
                from qtpynodeeditor import PortType, ConnectionPolicy
                from qtpynodeeditor.node_connection_interaction import NodeConnectionInteraction

                if self._locked:
                    return

                if not self.isSelected() and not (event.modifiers() & Qt.ControlModifier):
                    self._scene.clearSelection()

                node_geometry = self._node.geometry

                for port_to_check in (PortType.input, PortType.output):
                    port = node_geometry.check_hit_scene_point(port_to_check,
                                                               event.scenePos(),
                                                               self.sceneTransform())
                    if not port:
                        continue

                    connections = port.connections

                    if connections and port_to_check == PortType.input:
                        for conn in connections:
                            interaction = NodeConnectionInteraction(self._node, conn, self._scene)
                            interaction.disconnect(port_to_check)
                    elif port_to_check == PortType.output:
                        out_policy = port.connection_policy
                        if connections and out_policy == ConnectionPolicy.one:
                            conn, = connections
                            self._scene.delete_connection(conn)

                        connection = self._scene.create_connection(port)
                        connection.graphics_object.grabMouse()

                pos = QPoint(int(event.pos().x()), int(event.pos().y()))
                geom = self._node.geometry
                state = self._node.state
                if self._node.model.resizable() and geom.resize_rect.contains(pos):
                    state.resizing = True
                self._scene.node_dragging.emit(True)
            ngo.NodeGraphicsObject.mousePressEvent = custom_node_mouse_press

            import qtpynodeeditor.port as port_module
            original_connection_policy = port_module.Port.connection_policy.fget
            def custom_connection_policy(self):
                if self.port_type == PortType.input:
                    if hasattr(self.model, 'port_in_connection_policy'):
                        return self.model.port_in_connection_policy(self.index)
                    return ConnectionPolicy.many
                else:
                    return original_connection_policy(self)
            port_module.Port.connection_policy = property(custom_connection_policy)

            layout.addWidget(self._view)
        else:
            placeholder = QLabel(
                "工作流编辑器需要安装 qtpynodeeditor\n\n"
                "请运行: pip install qtpynodeeditor"
            )
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #666; font-size: 14px;")
            layout.addWidget(placeholder)

        return editor

    def _on_key_press(self, event):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QGraphicsView
        from qtpynodeeditor import NodeGraphicsObject, ConnectionGraphicsObject

        if event.key() == Qt.Key.Key_Delete:
            selected_items = self._scene.selectedItems()
            for item in selected_items:
                if isinstance(item, NodeGraphicsObject):
                    node = item.node
                    if node:
                        self._scene.remove_node(node)
                        self._is_modified = True
                elif isinstance(item, ConnectionGraphicsObject):
                    conn = item.connection
                    if conn:
                        self._scene.delete_connection(conn)
                        self._is_modified = True
        else:
            QGraphicsView.keyPressEvent(self._view, event)

    def _on_double_click(self, event):
        from PyQt6.QtWidgets import QGraphicsView
        from qtpynodeeditor import NodeGraphicsObject, ConnectionGraphicsObject

        item = self._view.itemAt(event.pos())
        if isinstance(item, NodeGraphicsObject):
            node = item.node
            model = node.model
            if model and model._node_type not in ("start", "end"):
                self._edit_node(model)
            event.accept()
        elif isinstance(item, ConnectionGraphicsObject):
            event.accept()
        else:
            QGraphicsView.mouseDoubleClickEvent(self._view, event)

    def _edit_node(self, model):
        dialog = NodeConfigDialog(
            model._node_type,
            model.config,
            self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            model._name = dialog.get_name()
            model.config = dialog.get_config()
            self._is_modified = True

    def _add_node(self, node_type: str):
        if not HAS_NODE_EDITOR or not self._scene:
            QMessageBox.warning(
                self, "提示",
                "工作流编辑器需要安装 qtpynodeeditor"
            )
            return

        node_def = get_node_type(node_type)
        if not node_def:
            return

        model_class = NODE_MODEL_CLASSES.get(node_type)

        if model_class:
            node = self._scene.create_node(model_class)
            self._nodes[node.id] = node
            self._is_modified = True
            logger.info(f"添加节点: {node_type}")

    def load_workflow(self, workflow_id: int):
        self.workflow_id = workflow_id
        data = self.workflow_service.get_workflow_data(workflow_id)

        workflow = data.get("workflow")
        if workflow:
            self.title_label.setText(workflow.name)

        if not HAS_NODE_EDITOR or not self._scene:
            return

        self._scene.clear_scene()
        self._nodes.clear()

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        node_map = {}
        for node_data in nodes:
            node_type = node_data.get("node_type")
            model_class = NODE_MODEL_CLASSES.get(node_type)

            if model_class:
                node = self._scene.create_node(model_class)
                model = node.model
                model.node_key = node_data.get("node_key", str(uuid.uuid4()))
                model._name = node_data.get("node_name", node_type)
                model.config = node_data.get("config_json", {})

                pos_x = node_data.get("pos_x", 0)
                pos_y = node_data.get("pos_y", 0)
                node.graphics_object.setPos(QPointF(pos_x, pos_y))

                node_map[model.node_key] = node
                self._nodes[node.id] = node

        for edge_data in edges:
            source_key = edge_data.get("source_node_key")
            target_key = edge_data.get("target_node_key")
            source_port_index = edge_data.get("source_port", 0)
            target_port_index = edge_data.get("target_port", 0)

            if source_key in node_map and target_key in node_map:
                source_node = node_map[source_key]
                target_node = node_map[target_key]

                source_ports = source_node[PortType.output]
                target_ports = target_node[PortType.input]

                if source_port_index >= len(source_ports) or target_port_index >= len(target_ports):
                    logger.warning(
                        f"跳过无效连接: 端口索引越出范围 "
                        f"(source_port={source_port_index}/{len(source_ports)}, "
                        f"target_port={target_port_index}/{len(target_ports)})"
                    )
                    continue

                source_port = source_ports[source_port_index]
                target_port = target_ports[target_port_index]

                if target_port.connections:
                    from qtpynodeeditor import ConnectionPolicy
                    target_policy = target_port.connection_policy
                    if target_policy == ConnectionPolicy.one:
                        logger.warning(
                            f"跳过重复连接: 目标端口只允许一个连接 "
                            f"(source={source_key}:{source_port_index}, "
                            f"target={target_key}:{target_port_index})"
                        )
                        continue

                    connection = self._scene.create_connection(source_port)
                    connection.connect_to(target_port)
                else:
                    self._scene.create_connection(source_port, target_port)

        self._is_modified = False
        logger.info(f"加载工作流: {workflow_id}")

    def save_workflow(self):
        if not self.workflow_id:
            name, ok = QInputDialog.getText(
                self, "保存工作流", "请输入工作流名称:"
            )
            if not ok or not name.strip():
                return

            self.workflow_id = self.workflow_service.create_workflow(name.strip())
            if not self.workflow_id:
                QMessageBox.critical(self, "错误", "创建工作流失败")
                return

        nodes = []
        edges = []

        if HAS_NODE_EDITOR and self._scene:
            for node_id, node in self._nodes.items():
                model = node.model
                if model:
                    pos = node.position
                    nodes.append({
                        "node_key": model.node_key,
                        "node_type": model._node_type,
                        "node_name": model.caption,
                        "pos_x": pos.x(),
                        "pos_y": pos.y(),
                        "config_json": model.config
                    })

            for conn in self._scene.connections:
                source_node = conn.output_node
                target_node = conn.input_node

                if source_node and target_node:
                    source_model = source_node.model
                    target_model = target_node.model

                    source_port_index = conn.get_port_index(PortType.output)
                    target_port_index = conn.get_port_index(PortType.input)

                    edges.append({
                        "source_node_key": source_model.node_key,
                        "target_node_key": target_model.node_key,
                        "source_port": source_port_index,
                        "target_port": target_port_index,
                        "condition_json": {}
                    })

        success = self.workflow_service.save_workflow_data(
            self.workflow_id, nodes, edges
        )

        if success:
            self._is_modified = False
            QMessageBox.information(self, "成功", "工作流保存成功")
            self.workflow_saved.emit()
            logger.info(f"工作流保存成功: {self.workflow_id}")
        else:
            QMessageBox.critical(self, "错误", "保存工作流失败")

    def execute_workflow(self):
        if self._is_modified:
            reply = QMessageBox.question(
                self, "提示",
                "工作流已修改，是否先保存?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_workflow()
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        if not self.workflow_id:
            QMessageBox.warning(self, "提示", "请先保存工作流")
            return

        from services.workflow_engine import WorkflowEngine
        from models.workflow_run import TriggerType

        engine = WorkflowEngine(self.workflow_service)
        run_id = engine.execute_workflow(self.workflow_id, TriggerType.MANUAL)

        QMessageBox.information(
            self, "成功",
            f"工作流已开始执行\n执行记录ID: {run_id}"
        )
        self.workflow_executed.emit(run_id)

    def is_modified(self) -> bool:
        return self._is_modified
