from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from PyQt6.QtGui import QColor


@dataclass
class NodeTypeDefinition:
    type_id: str
    display_name: str
    category: str
    description: str
    icon: Optional[str] = None
    color: str = "#4A90D9"
    input_ports: int = 1
    output_ports: int = 1
    default_config: Dict[str, Any] = field(default_factory=dict)
    config_schema: Dict[str, Any] = field(default_factory=dict)


NODE_TYPES: Dict[str, NodeTypeDefinition] = {
    "start": NodeTypeDefinition(
        type_id="start",
        display_name="开始",
        category="控制",
        description="工作流开始节点",
        color="#27AE60",
        input_ports=0,
        output_ports=1,
        default_config={},
        config_schema={}
    ),
    "end": NodeTypeDefinition(
        type_id="end",
        display_name="结束",
        category="控制",
        description="工作流结束节点",
        color="#E74C3C",
        input_ports=1,
        output_ports=0,
        default_config={},
        config_schema={}
    ),
    "script": NodeTypeDefinition(
        type_id="script",
        display_name="执行脚本",
        category="操作",
        description="执行指定的脚本",
        color="#3498DB",
        input_ports=1,
        output_ports=1,
        default_config={"script_id": None, "server_id": None},
        config_schema={
            "script_id": {"type": "integer", "label": "脚本ID", "required": True},
            "server_id": {"type": "integer", "label": "服务器ID", "required": True}
        }
    ),
    "ssh": NodeTypeDefinition(
        type_id="ssh",
        display_name="SSH命令",
        category="操作",
        description="在远程服务器执行SSH命令",
        color="#9B59B6",
        input_ports=1,
        output_ports=1,
        default_config={"server_id": None, "command": ""},
        config_schema={
            "server_id": {"type": "integer", "label": "服务器ID", "required": True},
            "command": {"type": "text", "label": "命令", "required": True}
        }
    ),
    "condition": NodeTypeDefinition(
        type_id="condition",
        display_name="条件判断",
        category="控制",
        description="根据条件选择执行分支",
        color="#F39C12",
        input_ports=1,
        output_ports=2,
        default_config={"expression": "true"},
        config_schema={
            "expression": {"type": "text", "label": "条件表达式", "required": True}
        }
    ),
    "delay": NodeTypeDefinition(
        type_id="delay",
        display_name="延迟",
        category="控制",
        description="延迟执行一段时间",
        color="#1ABC9C",
        input_ports=1,
        output_ports=1,
        default_config={"delay_seconds": 1},
        config_schema={
            "delay_seconds": {"type": "integer", "label": "延迟秒数", "required": True, "min": 1}
        }
    ),
}


def get_node_type(type_id: str) -> Optional[NodeTypeDefinition]:
    return NODE_TYPES.get(type_id)


def get_all_node_types() -> List[NodeTypeDefinition]:
    return list(NODE_TYPES.values())


def get_node_types_by_category() -> Dict[str, List[NodeTypeDefinition]]:
    categories: Dict[str, List[NodeTypeDefinition]] = {}
    for node_type in NODE_TYPES.values():
        if node_type.category not in categories:
            categories[node_type.category] = []
        categories[node_type.category].append(node_type)
    return categories


def get_node_color(type_id: str) -> QColor:
    node_type = get_node_type(type_id)
    if node_type:
        return QColor(node_type.color)
    return QColor("#4A90D9")
