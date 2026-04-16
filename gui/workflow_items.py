from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsEllipseItem, QGraphicsPathItem,
    QGraphicsTextItem, QGraphicsRectItem, QStyleOptionGraphicsItem, QStyle
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QFont,
    QLinearGradient, QRadialGradient, QPainterPathStroker
)
from typing import Optional, List, Dict, Any
import math


class NodeSignals(QObject):
    position_changed = pyqtSignal(int, float, float)
    selected = pyqtSignal(int)
    double_clicked = pyqtSignal(int)


class WorkflowNodeItem(QGraphicsItem):
    NODE_WIDTH = 160
    NODE_HEIGHT = 80
    PORT_RADIUS = 8

    TYPE_COLORS = {
        "start": QColor("#4CAF50"),
        "end": QColor("#F44336"),
        "script": QColor("#2196F3"),
        "delay": QColor("#FF9800"),
        "condition": QColor("#9C27B0"),
        "parallel": QColor("#00BCD4"),
        "merge": QColor("#795548"),
        "base": QColor("#607D8B")
    }

    def __init__(self, node_id: int, node_type: str, name: str,
                 x: float = 0, y: float = 0, config: Dict = None, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.config = config or {}
        self.status = "pending"
        self.input_ports = 1
        self.output_ports = 1

        self.signals = NodeSignals()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsToShape, True)

        self.setPos(x, y)
        self.setZValue(1)

        self._update_port_count()

    def _update_port_count(self):
        from core.node_types import NODE_TYPES
        node_class = NODE_TYPES.get(self.node_type)
        if node_class:
            self.input_ports = node_class.input_ports
            self.output_ports = node_class.output_ports

    def boundingRect(self) -> QRectF:
        return QRectF(
            -self.PORT_RADIUS - 2,
            -self.PORT_RADIUS - 2,
            self.NODE_WIDTH + 2 * self.PORT_RADIUS + 4,
            self.NODE_HEIGHT + 2 * self.PORT_RADIUS + 4
        )

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        base_color = self.TYPE_COLORS.get(self.node_type, self.TYPE_COLORS["base"])

        if self.status == "running":
            base_color = QColor("#FFC107")
        elif self.status == "success":
            base_color = QColor("#4CAF50")
        elif self.status == "failed":
            base_color = QColor("#F44336")

        gradient = QLinearGradient(0, 0, 0, self.NODE_HEIGHT)
        gradient.setColorAt(0, base_color.lighter(120))
        gradient.setColorAt(1, base_color)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        shadow_rect = QRectF(3, 3, self.NODE_WIDTH, self.NODE_HEIGHT)
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(shadow_rect, 8, 8)

        node_rect = QRectF(0, 0, self.NODE_WIDTH, self.NODE_HEIGHT)
        painter.setBrush(QBrush(gradient))
        if self.status == "failed":
            painter.setPen(QPen(QColor("#F44336"), 4))
        elif self.isSelected():
            painter.setPen(QPen(QColor("#1976D2"), 2))
        else:
            painter.setPen(QPen(base_color.darker(130), 1))
        painter.drawRoundedRect(node_rect, 8, 8)

        painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
        painter.drawLine(int(self.NODE_WIDTH * 0.1), 25, int(self.NODE_WIDTH * 0.9), 25)

        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)
        painter.setFont(font)

        text_rect = QRectF(5, 5, self.NODE_WIDTH - 10, 20)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.name)

        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        type_rect = QRectF(5, 28, self.NODE_WIDTH - 10, 20)
        painter.drawText(type_rect, Qt.AlignmentFlag.AlignCenter, f"[{self.node_type}]")

        self._draw_ports(painter)

    def _draw_ports(self, painter: QPainter):
        port_gradient = QRadialGradient(0, 0, self.PORT_RADIUS)
        port_gradient.setColorAt(0, QColor(255, 255, 255))
        port_gradient.setColorAt(0.7, QColor(200, 200, 200))
        port_gradient.setColorAt(1, QColor(150, 150, 150))

        painter.setBrush(QBrush(port_gradient))
        painter.setPen(QPen(QColor(100, 100, 100), 1))

        if self.input_ports > 0:
            for i in range(max(1, self.input_ports)):
                y = self.NODE_HEIGHT / 2 if self.input_ports == 1 else (i + 1) * self.NODE_HEIGHT / (self.input_ports + 1)
                painter.drawEllipse(QPointF(-self.PORT_RADIUS, y), self.PORT_RADIUS, self.PORT_RADIUS)

        if self.output_ports > 0:
            for i in range(max(1, self.output_ports)):
                y = self.NODE_HEIGHT / 2 if self.output_ports == 1 else (i + 1) * self.NODE_HEIGHT / (self.output_ports + 1)
                painter.drawEllipse(QPointF(self.NODE_WIDTH + self.PORT_RADIUS, y), self.PORT_RADIUS, self.PORT_RADIUS)

    def get_input_port_pos(self, port_index: int = 0) -> QPointF:
        if self.input_ports <= 1:
            y = self.NODE_HEIGHT / 2
        else:
            y = (port_index + 1) * self.NODE_HEIGHT / (self.input_ports + 1)
        return self.pos() + QPointF(-self.PORT_RADIUS, y)

    def get_output_port_pos(self, port_index: int = 0) -> QPointF:
        if self.output_ports <= 1:
            y = self.NODE_HEIGHT / 2
        else:
            y = (port_index + 1) * self.NODE_HEIGHT / (self.output_ports + 1)
        return self.pos() + QPointF(self.NODE_WIDTH + self.PORT_RADIUS, y)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.signals.position_changed.emit(self.node_id, self.pos().x(), self.pos().y())
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self.signals.selected.emit(self.node_id)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        self.signals.double_clicked.emit(self.node_id)
        super().mouseDoubleClickEvent(event)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "config": self.config
        }

    def set_status(self, status: str):
        self.status = status
        self.update()


class ConnectionItem(QGraphicsPathItem):
    ARROW_SIZE = 20

    def __init__(self, source_node: WorkflowNodeItem, target_node: WorkflowNodeItem,
                 source_port: int = 0, target_port: int = 0, parent=None):
        super().__init__(parent)
        self.source_node = source_node
        self.target_node = target_node
        self.source_port = source_port
        self.target_port = target_port
        self._end_point = QPointF()
        self._arrow_direction = QPointF(1, 0)

        self.setZValue(0)
        self.setPen(QPen(QColor("#666666"), 2))
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        self._update_path()

    def _update_path(self):
        start = self.source_node.get_output_port_pos(self.source_port)
        end = self.target_node.get_input_port_pos(self.target_port)
        self._end_point = end

        path = QPainterPath()
        path.moveTo(start)

        dx = end.x() - start.x()
        control_offset = min(abs(dx) * 0.5, 100)

        ctrl1 = QPointF(start.x() + control_offset, start.y())
        ctrl2 = QPointF(end.x() - control_offset, end.y())

        path.cubicTo(ctrl1, ctrl2, end)

        t = 0.95
        pre_end_x = (1-t)**3 * start.x() + 3*(1-t)**2*t * ctrl1.x() + 3*(1-t)*t**2 * ctrl2.x() + t**3 * end.x()
        pre_end_y = (1-t)**3 * start.y() + 3*(1-t)**2*t * ctrl1.y() + 3*(1-t)*t**2 * ctrl2.y() + t**3 * end.y()
        pre_end = QPointF(pre_end_x, pre_end_y)

        dir_x = end.x() - pre_end.x()
        dir_y = end.y() - pre_end.y()
        length = math.sqrt(dir_x**2 + dir_y**2)
        if length > 0:
            self._arrow_direction = QPointF(dir_x / length, dir_y / length)
        else:
            self._arrow_direction = QPointF(1, 0)

        self.setPath(path)

    def shape(self):
        path = self.path()
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        return stroker.createStroke(path)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isSelected():
            pen = QPen(QColor("#1976D2"), 3)
        else:
            pen = QPen(QColor("#666666"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

        option.state = option.state & ~QStyle.StateFlag.State_Selected

        super().paint(painter, option, widget)

        arrow_color = QColor("#1976D2") if self.isSelected() else QColor("#666666")
        painter.setBrush(QBrush(arrow_color))
        painter.setPen(QPen(arrow_color, 1))

        angle = math.atan2(self._arrow_direction.y(), self._arrow_direction.x())

        p1 = self._end_point
        p2 = QPointF(
            self._end_point.x() - self.ARROW_SIZE * math.cos(angle - math.pi / 6),
            self._end_point.y() - self.ARROW_SIZE * math.sin(angle - math.pi / 6)
        )
        p3 = QPointF(
            self._end_point.x() - self.ARROW_SIZE * math.cos(angle + math.pi / 6),
            self._end_point.y() - self.ARROW_SIZE * math.sin(angle + math.pi / 6)
        )

        arrow_path = QPainterPath()
        arrow_path.moveTo(p1)
        arrow_path.lineTo(p2)
        arrow_path.lineTo(p3)
        arrow_path.closeSubpath()

        painter.drawPath(arrow_path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_node.node_id,
            "target": self.target_node.node_id,
            "source_port": self.source_port,
            "target_port": self.target_port
        }


class TempConnectionItem(QGraphicsPathItem):
    def __init__(self, start_pos: QPointF, parent=None):
        super().__init__(parent)
        self.start_pos = start_pos
        self.end_pos = start_pos

        self.setZValue(2)
        self.setPen(QPen(QColor("#1976D2"), 2, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        self._update_path()

    def set_end_pos(self, pos: QPointF):
        self.end_pos = pos
        self._update_path()

    def _update_path(self):
        path = QPainterPath()
        path.moveTo(self.start_pos)

        dx = self.end_pos.x() - self.start_pos.x()
        control_offset = min(abs(dx) * 0.5, 100)

        ctrl1 = QPointF(self.start_pos.x() + control_offset, self.start_pos.y())
        ctrl2 = QPointF(self.end_pos.x() - control_offset, self.end_pos.y())

        path.cubicTo(ctrl1, ctrl2, self.end_pos)

        self.setPath(path)
