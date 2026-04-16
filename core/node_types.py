from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import time
import tempfile
import os
import re
import sys
from core.logger import get_logger

logger = get_logger(__name__)


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeResult:
    status: NodeStatus
    output: str = ""
    error: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


class BaseNode(ABC):
    node_type: str = "base"
    category: str = "general"
    display_name: str = "基础节点"
    description: str = "节点基类"
    input_ports: int = 1
    output_ports: int = 1

    def __init__(self, node_id: int, name: str, config: Dict[str, Any] = None):
        self.node_id = node_id
        self.name = name
        self.config = config or {}
        self.status = NodeStatus.PENDING
        self.result: Optional[NodeResult] = None

    @abstractmethod
    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        pass

    def validate_config(self) -> bool:
        return True

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }


class StartNode(BaseNode):
    node_type = "start"
    category = "control"
    display_name = "开始"
    description = "工作流起始节点"
    input_ports = 0
    output_ports = 1

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        self.status = NodeStatus.SUCCESS
        self.result = NodeResult(status=NodeStatus.SUCCESS, output="工作流开始")
        return self.result


class EndNode(BaseNode):
    node_type = "end"
    category = "control"
    display_name = "结束"
    description = "工作流结束节点"
    input_ports = 1
    output_ports = 0

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        self.status = NodeStatus.SUCCESS
        self.result = NodeResult(status=NodeStatus.SUCCESS, output="工作流结束")
        return self.result


class CommandNode(BaseNode):
    node_type = "command"
    category = "action"
    display_name = "命令执行"
    description = "执行Shell命令"
    input_ports = 1
    output_ports = 1

    def __init__(self, node_id: int, name: str, config: Dict[str, Any] = None):
        super().__init__(node_id, name, config)
        self.dict_service = None
        self.param_service = None

    def set_services(self, dict_service=None, param_service=None):
        self.dict_service = dict_service
        self.param_service = param_service

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "title": "命令",
                    "description": "要执行的Shell命令"
                },
                "timeout": {
                    "type": "integer",
                    "title": "超时时间(秒)",
                    "default": 300
                },
                "working_dir": {
                    "type": "string",
                    "title": "工作目录",
                    "default": ""
                }
            },
            "required": ["command"]
        }

    def _replace_variables(self, content: str) -> str:
        if not content:
            return content
        
        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split('.')
            
            if len(parts) < 2:
                return match.group(0)
            
            source_type = parts[0]
            
            try:
                if source_type == "dict" and self.dict_service:
                    if len(parts) >= 3:
                        dict_code = parts[1]
                        item_name = parts[2]
                        items = self.dict_service.get_dict_items(dict_code)
                        logger.info(f"字典变量替换: 查找字典 '{dict_code}' 中的项 '{item_name}'，共 {len(items)} 个字典项")
                        for item in items:
                            logger.info(f"  - 字典项: code='{item.item_code}', name='{item.item_name}'")
                            if item.item_name == item_name:
                                logger.info(f"字典变量替换成功: @{var_path} -> {item.item_code}")
                                return item.item_code
                        logger.warning(f"字典变量替换失败: 未找到匹配的字典项 @{var_path}")
                elif source_type == "dict" and not self.dict_service:
                    logger.warning(f"字典变量替换失败: dict_service 未设置 @{var_path}")
                elif source_type == "param" and self.param_service:
                    param_code = parts[1]
                    logger.debug(f"尝试替换参数变量: param_code={param_code}")
                    param = self.param_service.get_param_by_code(param_code)
                    if param:
                        logger.info(f"参数变量替换成功: @{var_path} -> {param.param_value}")
                        return param.param_value
                    else:
                        logger.warning(f"参数变量替换失败: 未找到参数 @{var_path}")
                elif source_type == "param" and not self.param_service:
                    logger.warning(f"参数变量替换失败: param_service 未设置 @{var_path}")
            except Exception as e:
                logger.error(f"变量替换异常: @{var_path}, 错误: {str(e)}")
            
            return match.group(0)
        
        pattern = r'@([a-zA-Z_][a-zA-Z0-9_\.]*)'
        return re.sub(pattern, replace_var, content)

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        inputs = inputs or {}
        command = self.config.get("command", "")
        timeout = self.config.get("timeout", 300)
        working_dir = self.config.get("working_dir") or None

        command = self._replace_variables(command)

        if inputs.get("output"):
            command = command.replace("${input}", str(inputs.get("output", "")))

        if not command:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error="未配置执行命令"
            )
            return self.result

        try:
            self.status = NodeStatus.RUNNING
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir
            )
            if result.returncode == 0:
                self.status = NodeStatus.SUCCESS
                self.result = NodeResult(
                    status=NodeStatus.SUCCESS,
                    output=result.stdout,
                    data={"return_code": result.returncode}
                )
            else:
                self.status = NodeStatus.FAILED
                self.result = NodeResult(
                    status=NodeStatus.FAILED,
                    output=result.stdout,
                    error=result.stderr
                )
        except subprocess.TimeoutExpired:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=f"命令执行超时，超过{timeout}秒"
            )
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=str(e)
            )

        return self.result


class ScriptNode(BaseNode):
    node_type = "script"
    category = "action"
    display_name = "脚本执行"
    description = "执行脚本管理中的脚本，支持Bash/Python/SQL"
    input_ports = 1
    output_ports = 1

    def __init__(self, node_id: int, name: str, config: Dict[str, Any] = None):
        super().__init__(node_id, name, config)
        self.dict_service = None
        self.param_service = None

    def set_services(self, dict_service=None, param_service=None):
        self.dict_service = dict_service
        self.param_service = param_service

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script_id": {
                    "type": "integer",
                    "title": "脚本",
                    "description": "从脚本管理中选择的脚本"
                },
                "script_content": {
                    "type": "string",
                    "title": "脚本内容",
                    "description": "脚本内容（由系统自动填充）",
                    "hidden": True
                },
                "script_language": {
                    "type": "string",
                    "title": "脚本语言",
                    "description": "脚本语言类型（bash/python/sql，由系统自动填充）",
                    "hidden": True
                },
                "script_name": {
                    "type": "string",
                    "title": "脚本名称",
                    "description": "脚本名称（由系统自动填充）",
                    "hidden": True
                },
                "timeout": {
                    "type": "integer",
                    "title": "超时时间(秒)",
                    "default": 300
                },
                "working_dir": {
                    "type": "string",
                    "title": "工作目录",
                    "default": ""
                }
            },
            "required": ["script_id"]
        }

    def _replace_variables(self, content: str) -> str:
        if not content:
            return content
        
        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split('.')
            
            if len(parts) < 2:
                return match.group(0)
            
            source_type = parts[0]
            
            try:
                if source_type == "dict" and self.dict_service:
                    if len(parts) >= 3:
                        dict_code = parts[1]
                        item_name = parts[2]
                        items = self.dict_service.get_dict_items(dict_code)
                        logger.info(f"字典变量替换: 查找字典 '{dict_code}' 中的项 '{item_name}'，共 {len(items)} 个字典项")
                        for item in items:
                            logger.info(f"  - 字典项: code='{item.item_code}', name='{item.item_name}'")
                            if item.item_name == item_name:
                                logger.info(f"字典变量替换成功: @{var_path} -> {item.item_code}")
                                return item.item_code
                        logger.warning(f"字典变量替换失败: 未找到匹配的字典项 @{var_path}")
                elif source_type == "dict" and not self.dict_service:
                    logger.warning(f"字典变量替换失败: dict_service 未设置 @{var_path}")
                elif source_type == "param" and self.param_service:
                    param_code = parts[1]
                    logger.debug(f"尝试替换参数变量: param_code={param_code}")
                    param = self.param_service.get_param_by_code(param_code)
                    if param:
                        logger.info(f"参数变量替换成功: @{var_path} -> {param.param_value}")
                        return param.param_value
                    else:
                        logger.warning(f"参数变量替换失败: 未找到参数 @{var_path}")
                elif source_type == "param" and not self.param_service:
                    logger.warning(f"参数变量替换失败: param_service 未设置 @{var_path}")
            except Exception as e:
                logger.error(f"变量替换异常: @{var_path}, 错误: {str(e)}")
            
            return match.group(0)
        
        pattern = r'@([a-zA-Z_][a-zA-Z0-9_\.]*)'
        return re.sub(pattern, replace_var, content)

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        inputs = inputs or {}
        script_content = self.config.get("script_content", "")
        script_language = self.config.get("script_language", "bash")
        script_name = self.config.get("script_name", "")
        timeout = self.config.get("timeout", 300)
        working_dir = self.config.get("working_dir") or None

        if not script_content:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error="未找到脚本内容，请确保已正确选择脚本"
            )
            return self.result

        script_content = self._replace_variables(script_content)
        command = self._build_command_for_language(script_content, script_language)

        if inputs.get("output"):
            command = command.replace("${input}", str(inputs.get("output", "")))

        try:
            self.status = NodeStatus.RUNNING
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir
            )
            if result.returncode == 0:
                self.status = NodeStatus.SUCCESS
                self.result = NodeResult(
                    status=NodeStatus.SUCCESS,
                    output=result.stdout,
                    data={"return_code": result.returncode, "script_name": script_name, "script_language": script_language}
                )
            else:
                self.status = NodeStatus.FAILED
                self.result = NodeResult(
                    status=NodeStatus.FAILED,
                    output=result.stdout,
                    error=result.stderr
                )
        except subprocess.TimeoutExpired:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=f"脚本执行超时，超过{timeout}秒"
            )
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=str(e)
            )

        return self.result
    
    def _build_command_for_language(self, script_content: str, language: str) -> str:
        if language == "python":
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_file = f.name
            return f'"{sys.executable}" {temp_file}'
        elif language == "sql":
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
                f.write(script_content)
                temp_file = f.name
            return f"sqlite3 :memory: < {temp_file}"
        else:
            return script_content


class DelayNode(BaseNode):
    node_type = "delay"
    category = "control"
    display_name = "延时"
    description = "等待指定时间"
    input_ports = 1
    output_ports = 1

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "delay_seconds": {
                    "type": "integer",
                    "title": "延时时间(秒)",
                    "default": 1
                }
            },
            "required": ["delay_seconds"]
        }

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        delay = self.config.get("delay_seconds", 1)
        self.status = NodeStatus.RUNNING
        time.sleep(delay)
        self.status = NodeStatus.SUCCESS
        self.result = NodeResult(
            status=NodeStatus.SUCCESS,
            output=f"延时{delay}秒完成"
        )
        return self.result


class ConditionNode(BaseNode):
    node_type = "condition"
    category = "control"
    display_name = "条件判断"
    description = "根据条件选择执行路径"
    input_ports = 1
    output_ports = 2

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "title": "条件表达式",
                    "description": "Python表达式，返回True或False"
                }
            },
            "required": ["condition"]
        }

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        inputs = inputs or {}
        condition = self.config.get("condition", "True")

        try:
            self.status = NodeStatus.RUNNING
            context = {"input": inputs.get("output", ""), "data": inputs.get("data", {})}
            result = eval(condition, {"__builtins__": {}}, context)
            self.status = NodeStatus.SUCCESS
            self.result = NodeResult(
                status=NodeStatus.SUCCESS,
                output=f"条件判断结果: {result}",
                data={"condition_result": bool(result)}
            )
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=f"条件表达式执行错误: {str(e)}"
            )

        return self.result


class ParallelNode(BaseNode):
    node_type = "parallel"
    category = "control"
    display_name = "并行执行"
    description = "并行执行多个分支"
    input_ports = 1
    output_ports = 1

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        self.status = NodeStatus.SUCCESS
        self.result = NodeResult(
            status=NodeStatus.SUCCESS,
            output="并行分支开始执行"
        )
        return self.result


class MergeNode(BaseNode):
    node_type = "merge"
    category = "control"
    display_name = "合并"
    description = "合并多个分支"
    input_ports = -1
    output_ports = 1

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        self.status = NodeStatus.SUCCESS
        self.result = NodeResult(
            status=NodeStatus.SUCCESS,
            output="分支合并完成"
        )
        return self.result


NODE_TYPES: Dict[str, type] = {
    "start": StartNode,
    "end": EndNode,
    "command": CommandNode,
    "script": ScriptNode,
    "delay": DelayNode,
    "condition": ConditionNode,
    "parallel": ParallelNode,
    "merge": MergeNode,
}


def get_node_class(node_type: str) -> type:
    return NODE_TYPES.get(node_type, BaseNode)


def get_all_node_types() -> Dict[str, Dict[str, Any]]:
    result = {}
    for node_type, node_class in NODE_TYPES.items():
        instance = node_class(0, "")
        result[node_type] = {
            "type": node_type,
            "category": node_class.category,
            "display_name": node_class.display_name,
            "description": node_class.description,
            "input_ports": node_class.input_ports,
            "output_ports": node_class.output_ports,
            "config_schema": instance.get_config_schema()
        }
    return result
