from PyQt5.QtWidgets import (
    QGraphicsView, QGraphicsScene, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QComboBox, QSpinBox,
    QScrollArea, QFrame, QDialog, QLineEdit, QTextEdit,
    QFormLayout, QDialogButtonBox, QMessageBox, QSplitter,
    QListWidget, QListWidgetItem, QGroupBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QApplication,
    QGraphicsItem, QShortcut
)
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QRectF, QTimer
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QIcon,
    QKeySequence, QStandardItemModel, QStandardItem
)
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget, PlotItem
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from gui.workflow_items import WorkflowNodeItem, ConnectionItem, TempConnectionItem
from core.node_types import get_all_node_types, NODE_TYPES
from core.logger import get_logger

logger = get_logger(__name__)


class NodeConfigDialog(QDialog):
    def __init__(self, node_item: WorkflowNodeItem, script_service=None, bastion_manager=None, parent=None):
        super().__init__(parent)
        self.node_item = node_item
        self.script_service = script_service
        self.bastion_manager = bastion_manager
        self.scripts = []
        self.setWindowTitle(f"节点配置 - {node_item.name}")
        self.setMinimumSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.name_edit = QLineEdit(self.node_item.name)
        form_layout.addRow("名称:", self.name_edit)

        layout.addLayout(form_layout)

        node_type_info = get_all_node_types().get(self.node_item.node_type, {})
        config_schema = node_type_info.get("config_schema", {}).get("properties", {})

        if config_schema:
            config_group = QGroupBox("节点配置")
            config_layout = QFormLayout(config_group)

            self.config_widgets = {}
            
            if self.node_item.node_type == "script" and self.script_service:
                self.scripts = self.script_service.get_all()
            
            for key, prop in config_schema.items():
                if prop.get("hidden"):
                    continue
                    
                label = prop.get("title", key)
                default = prop.get("default")
                current_value = self.node_item.config.get(key, default)

                if key == "script_id" and self.node_item.node_type == "script":
                    widget = QComboBox()
                    
                    model = QStandardItemModel()
                    root_item = model.invisibleRootItem()
                    
                    scripts_by_lang = {}
                    for script in self.scripts:
                        lang = script.language or "bash"
                        if lang not in scripts_by_lang:
                            scripts_by_lang[lang] = []
                        scripts_by_lang[lang].append(script)
                    
                    lang_names = {
                        "bash": "Bash脚本",
                        "python": "Python脚本",
                        "sql": "SQL脚本"
                    }
                    
                    please_select_item = QStandardItem("请选择脚本...")
                    please_select_item.setData(None, Qt.UserRole)
                    please_select_item.setData(None, Qt.UserRole + 1)
                    please_select_item.setData(None, Qt.UserRole + 2)
                    please_select_item.setFlags(please_select_item.flags() & ~Qt.ItemIsEnabled)
                    root_item.appendRow(please_select_item)
                    
                    for lang in ["bash", "python", "sql"]:
                        if lang in scripts_by_lang:
                            lang_item = QStandardItem(f"── {lang_names.get(lang, lang)} ──")
                            lang_item.setFlags(lang_item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                            lang_item.setData(None, Qt.UserRole)
                            lang_item.setData(None, Qt.UserRole + 1)
                            lang_item.setData(None, Qt.UserRole + 2)
                            root_item.appendRow(lang_item)
                            
                            for script in scripts_by_lang[lang]:
                                script_item = QStandardItem(f"  {script.id} - {script.name}")
                                script_item.setData(script.id, Qt.UserRole)
                                script_item.setData(lang, Qt.UserRole + 1)
                                script_item.setData(script.name, Qt.UserRole + 2)
                                root_item.appendRow(script_item)
                    
                    widget.setModel(model)
                    
                    if current_value:
                        self._select_script_in_combobox(widget, current_value)
                    
                    widget.currentIndexChanged.connect(self._on_script_selected)
                elif prop.get("enum"):
                    widget = QComboBox()
                    
                    enum_values = prop.get("enum", [])
                    enum_names = prop.get("enumNames", enum_values)
                    
                    for i, value in enumerate(enum_values):
                        display_name = enum_names[i] if i < len(enum_names) else value
                        widget.addItem(display_name, value)
                    
                    if current_value is not None:
                        index = widget.findData(current_value)
                        if index >= 0:
                            widget.setCurrentIndex(index)
                    
                    if prop.get("description"):
                        widget.setToolTip(prop.get("description"))
                elif prop.get("dynamicEnum") == "connected_hosts":
                    widget = QComboBox()
                    
                    widget.addItem("请选择主机...", None)
                    
                    if self.bastion_manager:
                        try:
                            hosts = self.bastion_manager.get_service().get_all_connected_hosts()
                            for host in hosts:
                                widget.addItem(host, host)
                        except Exception as e:
                            logger.warning(f"获取已连接主机列表失败: {e}")
                    
                    if current_value is not None:
                        index = widget.findData(current_value)
                        if index >= 0:
                            widget.setCurrentIndex(index)
                    
                    if prop.get("description"):
                        widget.setToolTip(prop.get("description"))
                elif prop.get("type") == "integer":
                    widget = QSpinBox()
                    widget.setMaximum(999999)
                    widget.setValue(int(current_value or 0))
                elif prop.get("type") == "boolean":
                    widget = QCheckBox()
                    widget.setChecked(bool(current_value))
                else:
                    widget = QLineEdit(str(current_value or ""))
                    if prop.get("placeholder"):
                        widget.setPlaceholderText(prop.get("placeholder"))
                    if prop.get("description"):
                        widget.setToolTip(prop.get("description"))

                self.config_widgets[key] = widget
                config_layout.addRow(f"{label}:", widget)

            layout.addWidget(config_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
            
    def _on_script_selected(self):
        if "script_id" not in self.config_widgets:
            return
            
        widget = self.config_widgets["script_id"]
        current_index = widget.currentIndex()
        if current_index < 0:
            return
            
        model = widget.model()
        item = model.itemFromIndex(model.index(current_index, 0))
        
        script_id = item.data(Qt.UserRole)
        script_lang = item.data(Qt.UserRole + 1)
        script_name = item.data(Qt.UserRole + 2)
        
        if script_id and self.scripts:
            for script in self.scripts:
                if script.id == script_id:
                    self.config_widgets["script_content"] = QLineEdit(script.content)
                    self.config_widgets["script_language"] = QLineEdit(script_lang or "bash")
                    self.config_widgets["script_name"] = QLineEdit(script_name or "")
                    break
    
    def _select_script_in_combobox(self, combobox: QComboBox, script_id: int):
        model = combobox.model()
        for i in range(model.rowCount()):
            index = model.index(i, 0)
            item = model.itemFromIndex(index)
            if item and item.data(Qt.UserRole) == script_id:
                combobox.setCurrentIndex(i)
                return

    def get_config(self) -> Dict[str, Any]:
        config = {}
        for key, widget in self.config_widgets.items():
            if isinstance(widget, QComboBox):
                model = widget.model()
                if isinstance(model, QStandardItemModel):
                    current_index = widget.currentIndex()
                    if current_index >= 0:
                        item = model.itemFromIndex(model.index(current_index, 0))
                        config[key] = item.data(Qt.UserRole)
                    else:
                        config[key] = None
                else:
                    config[key] = widget.currentData()
            elif isinstance(widget, QSpinBox):
                config[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                config[key] = widget.isChecked()
            else:
                config[key] = widget.text()
        return config

    def get_name(self) -> str:
        return self.name_edit.text()


class NodePaletteWidget(QWidget):
    node_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(220)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("节点类型")
        title.setObjectName("nodeTypeTitle")
        layout.addWidget(title)

        self.node_list = QListWidget()
        self.node_list.setDragEnabled(True)

        node_types = get_all_node_types()
        categories = {}
        for node_type, info in node_types.items():
            category = info.get("category", "general")
            if category not in categories:
                categories[category] = []
            categories[category].append((node_type, info))

        category_names = {
            "control": "控制节点",
            "action": "动作节点",
            "general": "通用节点",
            "environment": "环境切换节点"
        }

        for category, nodes in categories.items():
            category_item = QListWidgetItem(category_names.get(category, category))
            category_item.setFlags(category_item.flags() & ~Qt.ItemIsSelectable)
            category_item.setBackground(QColor(240, 240, 240))
            self.node_list.addItem(category_item)

            for node_type, info in nodes:
                item = QListWidgetItem(f"  {info['display_name']}")
                item.setData(Qt.UserRole, node_type)
                item.setToolTip(info['description'])
                self.node_list.addItem(item)

        self.node_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.node_list)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        node_type = item.data(Qt.UserRole)
        if node_type:
            self.node_selected.emit(node_type)


class WorkflowCanvas(QGraphicsView):
    node_added = pyqtSignal(WorkflowNodeItem)
    node_removed = pyqtSignal(int)
    node_config_changed = pyqtSignal(int, str, dict)
    connection_added = pyqtSignal(ConnectionItem)
    connection_removed = pyqtSignal(tuple)
    selection_changed = pyqtSignal(list)

    def __init__(self, script_service=None, bastion_manager=None, mode="edit", parent=None):
        super().__init__(parent)
        self.script_service = script_service
        self.bastion_manager = bastion_manager
        self.mode = mode
        self._read_only = (mode == "execute")
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.scene.setBackgroundBrush(QBrush(QColor(245, 245, 245)))

        self.nodes: Dict[int, WorkflowNodeItem] = {}
        self.connections: List[ConnectionItem] = []
        self.next_node_id = 1

        self._is_connecting = False
        self._connection_start_node: Optional[WorkflowNodeItem] = None
        self._temp_connection: Optional[TempConnectionItem] = None

        self._pan_mode = False
        self._last_mouse_pos = QPointF()
        self._clipboard = []

        self._init_shortcuts()
        
        if self._read_only:
            self._set_read_only_mode()

    def _init_shortcuts(self):
        delete_shortcut = QShortcut(QKeySequence.Delete, self)
        delete_shortcut.activated.connect(self.delete_selected)

        copy_shortcut = QShortcut(QKeySequence.Copy, self)
        copy_shortcut.activated.connect(self.copy_selected)

        paste_shortcut = QShortcut(QKeySequence.Paste, self)
        paste_shortcut.activated.connect(self.paste)

    def _set_read_only_mode(self):
        for node in self.nodes.values():
            node.setFlag(QGraphicsItem.ItemIsMovable, False)
        
        for conn in self.connections:
            conn.setFlag(QGraphicsItem.ItemIsSelectable, False)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, QColor(245, 245, 245))
        
        grid_pen = QPen(QColor(220, 220, 220), 1)
        painter.setPen(grid_pen)
        
        grid_size = 50
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        
        x = left
        while x <= rect.right():
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += grid_size
        
        y = top
        while y <= rect.bottom():
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += grid_size

    def add_node(self, node_type: str, x: float, y: float,
                 name: str = None, config: Dict = None, node_id: int = None) -> WorkflowNodeItem:
        if node_id is None:
            node_id = self.next_node_id
            self.next_node_id += 1
        else:
            self.next_node_id = max(self.next_node_id, node_id + 1)

        if name is None:
            node_info = get_all_node_types().get(node_type, {})
            name = node_info.get("display_name", f"节点{node_id}")

        node = WorkflowNodeItem(node_id, node_type, name, x, y, config)
        node.signals.position_changed.connect(self._on_node_moved)
        node.signals.double_clicked.connect(self._on_node_double_clicked)

        self.scene.addItem(node)
        self.nodes[node_id] = node
        
        if self._read_only:
            node.setFlag(QGraphicsItem.ItemIsMovable, False)

        self.node_added.emit(node)
        return node

    def remove_node(self, node_id: int):
        if self._read_only:
            return
            
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]

        conns_to_remove = [c for c in self.connections
                          if c.source_node.node_id == node_id or c.target_node.node_id == node_id]
        for conn in conns_to_remove:
            self.remove_connection(conn)

        self.scene.removeItem(node)
        del self.nodes[node_id]
        self.node_removed.emit(node_id)

    def add_connection(self, source_id: int, target_id: int,
                       source_port: int = 0, target_port: int = 0) -> Optional[ConnectionItem]:
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        source_node = self.nodes[source_id]
        target_node = self.nodes[target_id]

        for conn in self.connections:
            if (conn.source_node.node_id == source_id and
                conn.target_node.node_id == target_id):
                return None

        connection = ConnectionItem(source_node, target_node, source_port, target_port)
        self.scene.addItem(connection)
        self.connections.append(connection)
        
        if self._read_only:
            connection.setFlag(QGraphicsItem.ItemIsSelectable, False)

        self.connection_added.emit(connection)
        return connection

    def remove_connection(self, connection: ConnectionItem):
        if self._read_only:
            return
            
        if connection in self.connections:
            self.connections.remove(connection)
            self.scene.removeItem(connection)
            self.connection_removed.emit((connection.source_node.node_id,
                                         connection.target_node.node_id))

    def clear_all(self):
        for conn in self.connections[:]:
            self.scene.removeItem(conn)
        self.connections.clear()

        for node in self.nodes.values():
            self.scene.removeItem(node)
        self.nodes.clear()

        self.next_node_id = 1

    def get_graph_data(self) -> Dict[str, Any]:
        nodes = [node.to_dict() for node in self.nodes.values()]
        connections = [conn.to_dict() for conn in self.connections]
        return {"nodes": nodes, "connections": connections}

    def load_graph_data(self, data: Dict[str, Any]):
        self.clear_all()

        nodes = data.get("nodes", [])
        connections = data.get("connections", [])

        for node_data in nodes:
            self.add_node(
                node_type=node_data.get("node_type", "base"),
                x=node_data.get("x", 0),
                y=node_data.get("y", 0),
                name=node_data.get("name"),
                config=node_data.get("config"),
                node_id=node_data.get("id")
            )

        for conn_data in connections:
            self.add_connection(
                source_id=conn_data.get("source"),
                target_id=conn_data.get("target"),
                source_port=conn_data.get("source_port", 0),
                target_port=conn_data.get("target_port", 0)
            )
        
        if self._read_only:
            self._set_read_only_mode()

    def delete_selected(self):
        if self._read_only:
            return
            
        selected_connections = [item for item in self.scene.selectedItems()
                              if isinstance(item, ConnectionItem)]
        for conn in selected_connections:
            self.remove_connection(conn)

        selected_nodes = [item for item in self.scene.selectedItems()
                        if isinstance(item, WorkflowNodeItem)]

        for node in selected_nodes:
            self.remove_node(node.node_id)

    def copy_selected(self):
        if self._read_only:
            return
            
        selected_nodes = [item for item in self.scene.selectedItems()
                        if isinstance(item, WorkflowNodeItem)]
        if selected_nodes:
            self._clipboard = [node.to_dict() for node in selected_nodes]

    def paste(self):
        if self._read_only:
            return
            
        if self._clipboard:
            for node_data in self._clipboard:
                self.add_node(
                    node_type=node_data["node_type"],
                    x=node_data["x"] + 50,
                    y=node_data["y"] + 50,
                    name=node_data["name"] + " (副本)",
                    config=node_data.get("config")
                )

    def _on_node_moved(self, node_id: int, x: float, y: float):
        for conn in self.connections:
            if conn.source_node.node_id == node_id or conn.target_node.node_id == node_id:
                conn._update_path()

    def _on_node_double_clicked(self, node_id: int):
        if self._read_only:
            return
            
        if node_id in self.nodes:
            node = self.nodes[node_id]
            dialog = NodeConfigDialog(node, self.script_service, self.bastion_manager, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_name = dialog.get_name()
                new_config = dialog.get_config()
                node.name = new_name
                node.config = new_config
                node.update()
                self.node_config_changed.emit(node_id, new_name, new_config)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan_mode = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton and not self._read_only:
            item = self.itemAt(event.pos())
            if isinstance(item, WorkflowNodeItem):
                port_pos = self._get_port_at_position(item, event.pos())
                if port_pos is not None:
                    self._is_connecting = True
                    self._connection_start_node = item
                    scene_pos = self.mapToScene(event.pos())
                    self._temp_connection = TempConnectionItem(scene_pos)
                    self.scene.addItem(self._temp_connection)
                    event.accept()
                    return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_mode:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return

        if self._is_connecting and self._temp_connection:
            scene_pos = self.mapToScene(event.pos())
            self._temp_connection.set_end_pos(scene_pos)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan_mode = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton and self._is_connecting:
            self._is_connecting = False

            if self._temp_connection:
                self.scene.removeItem(self._temp_connection)
                self._temp_connection = None

            item = self.itemAt(event.pos())
            if isinstance(item, WorkflowNodeItem) and item != self._connection_start_node:
                self.add_connection(
                    self._connection_start_node.node_id,
                    item.node_id
                )

            self._connection_start_node = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor

        self.scale(factor, factor)

    def _get_port_at_position(self, node: WorkflowNodeItem, pos) -> Optional[int]:
        scene_pos = self.mapToScene(pos)
        node_rect = node.boundingRect().translated(node.pos())

        input_port_x = node.pos().x() - WorkflowNodeItem.PORT_RADIUS
        output_port_x = node.pos().x() + WorkflowNodeItem.NODE_WIDTH + WorkflowNodeItem.PORT_RADIUS

        if abs(scene_pos.x() - output_port_x) < WorkflowNodeItem.PORT_RADIUS * 2:
            return 0

        if abs(scene_pos.x() - input_port_x) < WorkflowNodeItem.PORT_RADIUS * 2:
            return -1

        return None

    def set_node_status(self, node_id: int, status: str):
        if node_id in self.nodes:
            self.nodes[node_id].set_status(status)

    def reset_all_status(self):
        for node in self.nodes.values():
            node.set_status("pending")

    def fit_to_view(self):
        if not self.nodes:
            return

        rect = QRectF()
        for node in self.nodes.values():
            rect = rect.united(node.boundingRect().translated(node.pos()))

        rect.adjust(-50, -50, 50, 50)
        self.fitInView(rect, Qt.KeepAspectRatio)
