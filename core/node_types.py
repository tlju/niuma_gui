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


class MinioNode(BaseNode):
    node_type = "minio"
    category = "action"
    display_name = "MinIO操作"
    description = "执行MinIO对象存储操作，支持上传、下载、删除、列表、复制、移动等操作"
    input_ports = 1
    output_ports = 1

    def __init__(self, node_id: int, name: str, config: Dict[str, Any] = None):
        super().__init__(node_id, name, config)
        self.db = None

    def set_services(self, db=None, **kwargs):
        self.db = db

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "title": "操作类型",
                    "description": "选择要执行的MinIO操作类型",
                    "enum": ["upload", "download", "delete", "list", "copy", "move", "exists", "info"],
                    "enumNames": ["上传文件", "下载文件", "删除文件", "列出文件", "复制文件", "移动文件", "检查文件存在", "获取文件信息"]
                },
                "object_name": {
                    "type": "string",
                    "title": "对象名称",
                    "description": "MinIO存储桶中的对象路径，支持文件夹结构。例如：documents/report.pdf 或 images/photo.jpg。支持使用变量 @input.output 引用上游节点输出。",
                    "placeholder": "例如: folder/file.txt"
                },
                "file_path": {
                    "type": "string",
                    "title": "本地文件路径",
                    "description": "本地文件的完整路径。上传时为源文件路径，下载时为目标保存路径。支持使用变量 @input.output 引用上游节点输出。",
                    "placeholder": "例如: /tmp/upload/file.txt 或 /tmp/download/file.txt"
                },
                "source_name": {
                    "type": "string",
                    "title": "源对象名称",
                    "description": "复制或移动操作的源对象路径。例如：documents/old_report.pdf",
                    "placeholder": "例如: folder/source.txt"
                },
                "dest_name": {
                    "type": "string",
                    "title": "目标对象名称",
                    "description": "复制或移动操作的目标对象路径。例如：documents/new_report.pdf",
                    "placeholder": "例如: folder/destination.txt"
                },
                "prefix": {
                    "type": "string",
                    "title": "前缀",
                    "description": "列出文件时使用的对象前缀，用于筛选特定目录下的文件。留空则列出所有文件。",
                    "default": "",
                    "placeholder": "例如: documents/ 或 images/"
                },
                "recursive": {
                    "type": "boolean",
                    "title": "递归列出",
                    "description": "列出文件时是否递归查找子目录。开启后会列出所有层级的文件。",
                    "default": False
                },
                "content_type": {
                    "type": "string",
                    "title": "内容类型",
                    "description": "上传文件时指定的MIME类型，用于标识文件格式",
                    "default": "application/octet-stream",
                    "enum": [
                        "application/octet-stream",
                        "text/plain",
                        "text/html",
                        "text/css",
                        "text/javascript",
                        "application/json",
                        "application/xml",
                        "application/pdf",
                        "application/zip",
                        "application/x-tar",
                        "application/gzip",
                        "image/jpeg",
                        "image/png",
                        "image/gif",
                        "image/svg+xml",
                        "video/mp4",
                        "video/mpeg",
                        "audio/mpeg",
                        "audio/wav",
                        "application/vnd.ms-excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ],
                    "enumNames": [
                        "二进制文件（默认）",
                        "纯文本文件",
                        "HTML文件",
                        "CSS样式表",
                        "JavaScript脚本",
                        "JSON数据",
                        "XML数据",
                        "PDF文档",
                        "ZIP压缩包",
                        "TAR归档文件",
                        "GZIP压缩文件",
                        "JPEG图片",
                        "PNG图片",
                        "GIF图片",
                        "SVG矢量图",
                        "MP4视频",
                        "MPEG视频",
                        "MP3音频",
                        "WAV音频",
                        "Excel文档",
                        "Excel文档",
                        "Word文档",
                        "Word文档"
                    ]
                }
            },
            "required": ["operation"]
        }

    def _replace_variables(self, content: str, inputs: Dict[str, Any] = None) -> str:
        if not content:
            return content
        
        inputs = inputs or {}
        
        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split('.')
            
            if len(parts) < 2:
                return match.group(0)
            
            source_type = parts[0]
            
            try:
                if source_type == "input":
                    return str(inputs.get("output", ""))
            except Exception as e:
                logger.error(f"变量替换异常: @{var_path}, 错误: {str(e)}")
            
            return match.group(0)
        
        pattern = r'@([a-zA-Z_][a-zA-Z0-9_\.]*)'
        return re.sub(pattern, replace_var, content)

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        from services.minio_service import MinioService
        
        inputs = inputs or {}
        
        if not self.db:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error="数据库会话未设置，无法获取MinIO配置"
            )
            return self.result

        operation = self.config.get("operation")
        if not operation:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error="未指定操作类型"
            )
            return self.result

        try:
            self.status = NodeStatus.RUNNING
            
            minio_service = MinioService(db=self.db)
            
            result_data = {}
            output_msg = ""
            
            if operation == "upload":
                object_name = self._replace_variables(self.config.get("object_name", ""), inputs)
                file_path = self._replace_variables(self.config.get("file_path", ""), inputs)
                content_type = self.config.get("content_type", "application/octet-stream")
                
                if not object_name or not file_path:
                    raise ValueError("上传操作需要指定对象名称和本地文件路径")
                
                success = minio_service.upload_file(object_name, file_path, content_type)
                if success:
                    output_msg = f"文件上传成功: {file_path} -> {object_name}"
                    result_data = {"object_name": object_name, "file_path": file_path}
                else:
                    raise Exception(f"文件上传失败: {file_path} -> {object_name}")
                    
            elif operation == "download":
                object_name = self._replace_variables(self.config.get("object_name", ""), inputs)
                file_path = self._replace_variables(self.config.get("file_path", ""), inputs)
                
                if not object_name or not file_path:
                    raise ValueError("下载操作需要指定对象名称和本地文件路径")
                
                success = minio_service.download_file(object_name, file_path)
                if success:
                    output_msg = f"文件下载成功: {object_name} -> {file_path}"
                    result_data = {"object_name": object_name, "file_path": file_path}
                else:
                    raise Exception(f"文件下载失败: {object_name} -> {file_path}")
                    
            elif operation == "delete":
                object_name = self._replace_variables(self.config.get("object_name", ""), inputs)
                
                if not object_name:
                    raise ValueError("删除操作需要指定对象名称")
                
                success = minio_service.delete_file(object_name)
                if success:
                    output_msg = f"文件删除成功: {object_name}"
                    result_data = {"object_name": object_name}
                else:
                    raise Exception(f"文件删除失败: {object_name}")
                    
            elif operation == "list":
                prefix = self._replace_variables(self.config.get("prefix", ""), inputs)
                recursive = self.config.get("recursive", False)
                
                files = minio_service.list_files(prefix, recursive)
                file_list = [f.to_dict() for f in files]
                output_msg = f"列出文件成功，共 {len(files)} 个文件"
                result_data = {"files": file_list, "count": len(files)}
                
            elif operation == "copy":
                source_name = self._replace_variables(self.config.get("source_name", ""), inputs)
                dest_name = self._replace_variables(self.config.get("dest_name", ""), inputs)
                
                if not source_name or not dest_name:
                    raise ValueError("复制操作需要指定源对象名称和目标对象名称")
                
                success = minio_service.copy_file(source_name, dest_name)
                if success:
                    output_msg = f"文件复制成功: {source_name} -> {dest_name}"
                    result_data = {"source_name": source_name, "dest_name": dest_name}
                else:
                    raise Exception(f"文件复制失败: {source_name} -> {dest_name}")
                    
            elif operation == "move":
                source_name = self._replace_variables(self.config.get("source_name", ""), inputs)
                dest_name = self._replace_variables(self.config.get("dest_name", ""), inputs)
                
                if not source_name or not dest_name:
                    raise ValueError("移动操作需要指定源对象名称和目标对象名称")
                
                success = minio_service.move_file(source_name, dest_name)
                if success:
                    output_msg = f"文件移动成功: {source_name} -> {dest_name}"
                    result_data = {"source_name": source_name, "dest_name": dest_name}
                else:
                    raise Exception(f"文件移动失败: {source_name} -> {dest_name}")
                    
            elif operation == "exists":
                object_name = self._replace_variables(self.config.get("object_name", ""), inputs)
                
                if not object_name:
                    raise ValueError("检查文件存在操作需要指定对象名称")
                
                exists = minio_service.file_exists(object_name)
                output_msg = f"文件{'存在' if exists else '不存在'}: {object_name}"
                result_data = {"object_name": object_name, "exists": exists}
                
            elif operation == "info":
                object_name = self._replace_variables(self.config.get("object_name", ""), inputs)
                
                if not object_name:
                    raise ValueError("获取文件信息操作需要指定对象名称")
                
                info = minio_service.get_file_info(object_name)
                if info:
                    output_msg = f"获取文件信息成功: {object_name}"
                    result_data = {"file_info": info.to_dict()}
                else:
                    raise Exception(f"文件不存在或获取信息失败: {object_name}")
            else:
                raise ValueError(f"不支持的操作类型: {operation}")
            
            self.status = NodeStatus.SUCCESS
            self.result = NodeResult(
                status=NodeStatus.SUCCESS,
                output=output_msg,
                data=result_data
            )
            
        except ValueError as e:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=f"配置错误: {str(e)}"
            )
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=f"MinIO操作失败: {str(e)}"
            )
        
        return self.result


class BastionNode(BaseNode):
    node_type = "bastion"
    category = "action"
    display_name = "堡垒机连接"
    description = "连接齐治堡垒机，支持二次认证、连接目标主机和通道保活"
    input_ports = 1
    output_ports = 1

    def __init__(self, node_id: int, name: str, config: Dict[str, Any] = None):
        super().__init__(node_id, name, config)
        self.db = None
        self._host_channel = None

    def set_services(self, db=None, **kwargs):
        self.db = db

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "title": "操作类型",
                    "description": "选择要执行的堡垒机操作",
                    "enum": ["connect", "connect_host", "disconnect", "execute", "get_ips", "status"],
                    "enumNames": ["连接堡垒机", "连接目标主机", "断开连接", "执行命令", "获取主机IP", "查询状态"],
                    "default": "connect"
                },
                "connection_id": {
                    "type": "string",
                    "title": "连接标识",
                    "description": "堡垒机连接的唯一标识符，用于管理多个连接",
                    "default": "default",
                    "placeholder": "例如: default, prod, test"
                },
                "target_host": {
                    "type": "string",
                    "title": "目标主机地址",
                    "description": "要通过堡垒机连接的目标主机IP或主机名，支持使用变量 @input.output 引用上游节点输出"
                },
                "target_username": {
                    "type": "string",
                    "title": "目标主机用户名",
                    "description": "目标主机的SSH用户名，支持使用变量引用"
                },
                "target_password": {
                    "type": "string",
                    "title": "目标主机密码",
                    "description": "目标主机的SSH密码，支持使用变量 @param.参数代码 引用系统参数"
                },
                "auth_type": {
                    "type": "string",
                    "title": "二次认证类型",
                    "description": "齐治堡垒机的二次认证方式",
                    "enum": ["password", "otp", "menu"],
                    "enumNames": ["密码认证", "动态口令(OTP)", "菜单选择"],
                    "default": "password"
                },
                "secondary_password": {
                    "type": "string",
                    "title": "二次认证密码",
                    "description": "二次认证所需的密码，支持使用变量 @param.参数代码 引用系统参数"
                },
                "otp_code": {
                    "type": "string",
                    "title": "动态口令",
                    "description": "OTP动态口令，支持使用变量引用"
                },
                "menu_selection": {
                    "type": "string",
                    "title": "菜单选择",
                    "description": "菜单选择项，例如选择目标服务器编号"
                },
                "command": {
                    "type": "string",
                    "title": "执行命令",
                    "description": "在堡垒机通道中执行的命令，连接目标主机后将在目标主机上执行",
                    "placeholder": "例如: ls -la, df -h"
                },
                "use_existing_connection": {
                    "type": "boolean",
                    "title": "使用已有连接",
                    "description": "是否使用系统已建立的堡垒机连接（自动登录的连接）",
                    "default": True
                },
                "keepalive_enabled": {
                    "type": "boolean",
                    "title": "启用保活",
                    "description": "是否启用通道保活功能",
                    "default": True
                },
                "keepalive_interval": {
                    "type": "integer",
                    "title": "保活间隔(秒)",
                    "description": "保活心跳间隔时间",
                    "default": 30,
                    "minimum": 10,
                    "maximum": 300
                },
                "min_channels": {
                    "type": "integer",
                    "title": "最小通道数",
                    "description": "保持活跃的最小通道数量",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 5
                },
                "max_channels": {
                    "type": "integer",
                    "title": "最大通道数",
                    "description": "允许创建的最大通道数量",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                },
                "timeout": {
                    "type": "integer",
                    "title": "超时时间(秒)",
                    "description": "连接和操作的超时时间",
                    "default": 30,
                    "minimum": 5,
                    "maximum": 300
                }
            },
            "required": ["operation"]
        }

    def _replace_variables(self, content: str, inputs: Dict[str, Any] = None) -> str:
        if not content:
            return content
        
        inputs = inputs or {}
        
        def replace_var(match):
            var_path = match.group(1)
            parts = var_path.split('.')
            
            if len(parts) < 2:
                return match.group(0)
            
            source_type = parts[0]
            
            try:
                if source_type == "input":
                    return str(inputs.get("output", ""))
                elif source_type == "param" and self.db:
                    from services.param_service import ParamService
                    param_service = ParamService(self.db)
                    param_code = parts[1]
                    param = param_service.get_param_by_code(param_code)
                    if param:
                        logger.info(f"参数变量替换成功: @{var_path} -> {param.param_value}")
                        return param.param_value
                    else:
                        logger.warning(f"参数变量替换失败: 未找到参数 @{var_path}")
            except Exception as e:
                logger.error(f"变量替换异常: @{var_path}, 错误: {str(e)}")
            
            return match.group(0)
        
        pattern = r'@([a-zA-Z_][a-zA-Z0-9_\.]*)'
        return re.sub(pattern, replace_var, content)

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        from services.bastion_service import BastionService, ConnectionStatus
        
        inputs = inputs or {}
        
        if not self.db:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error="数据库会话未设置，无法获取堡垒机配置"
            )
            return self.result

        operation = self.config.get("operation")
        if not operation:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error="未指定操作类型"
            )
            return self.result

        try:
            self.status = NodeStatus.RUNNING
            bastion_service = BastionService(db=self.db)
            
            result_data = {}
            output_msg = ""
            
            use_existing = self.config.get("use_existing_connection", True)
            connection_id = self.config.get("connection_id", "default")
            
            if operation == "connect":
                auth_type = self.config.get("auth_type", "password")
                secondary_password = self._replace_variables(self.config.get("secondary_password", ""), inputs)
                otp_code = self._replace_variables(self.config.get("otp_code", ""), inputs)
                menu_selection = self.config.get("menu_selection", "")
                timeout = self.config.get("timeout", 30)
                keepalive_enabled = self.config.get("keepalive_enabled", True)
                keepalive_interval = self.config.get("keepalive_interval", 30)
                min_channels = self.config.get("min_channels", 1)
                max_channels = self.config.get("max_channels", 5)
                
                connection = bastion_service.connect(connection_id=connection_id, timeout=timeout)
                
                bastion_service.authenticate(
                    connection_id=connection_id,
                    auth_type=auth_type,
                    secondary_password=secondary_password if secondary_password else None,
                    otp_code=otp_code if otp_code else None,
                    menu_selection=menu_selection if menu_selection else None
                )
                
                if keepalive_enabled:
                    bastion_service.start_keepalive(
                        connection_id=connection_id,
                        interval=keepalive_interval,
                        min_channels=min_channels,
                        max_channels=max_channels
                    )
                
                status = bastion_service.get_connection_status(connection_id)
                output_msg = f"堡垒机连接成功: {status['host']} (用户: {status['username']}, 通道数: {status['channels']})"
                result_data = {
                    "connection_id": connection_id,
                    "status": status,
                    "keepalive_enabled": keepalive_enabled
                }
                
            elif operation == "connect_host":
                target_host = self._replace_variables(self.config.get("target_host", ""), inputs)
                target_username = self._replace_variables(self.config.get("target_username", ""), inputs)
                target_password = self._replace_variables(self.config.get("target_password", ""), inputs)
                timeout = self.config.get("timeout", 30)
                
                if not target_host:
                    raise ValueError("连接目标主机需要指定目标主机地址")
                
                status = bastion_service.get_connection_status(connection_id)
                if not status.get("authenticated"):
                    raise Exception("堡垒机未连接或未完成认证，请先连接堡垒机")
                
                channel = bastion_service.connect_to_host(
                    connection_id=connection_id,
                    host=target_host,
                    username=target_username if target_username else None,
                    password=target_password if target_password else None,
                    timeout=timeout
                )
                
                if channel:
                    self._host_channel = channel
                    output_msg = f"成功连接到目标主机: {target_host}"
                    result_data = {
                        "target_host": target_host,
                        "channel_id": channel.channel_id,
                        "connected": True
                    }
                else:
                    raise Exception(f"连接目标主机 {target_host} 失败")
                    
            elif operation == "get_ips":
                timeout = self.config.get("timeout", 30)
                
                status = bastion_service.get_connection_status(connection_id)
                if not status.get("authenticated"):
                    raise Exception("堡垒机未连接或未完成认证")
                
                channel = self._host_channel or bastion_service.get_channel(connection_id)
                if not channel:
                    raise Exception("无法获取可用通道，请先连接目标主机")
                
                ips = bastion_service.get_host_ips(connection_id, channel, timeout)
                
                if ips:
                    output_msg = f"获取到 {len(ips)} 个IP地址: {', '.join(ips)}"
                    result_data = {
                        "ips": ips,
                        "count": len(ips),
                        "target_host": channel.target_host
                    }
                else:
                    output_msg = "未获取到IP地址"
                    result_data = {"ips": [], "count": 0}
                    
            elif operation == "disconnect":
                bastion_service.disconnect(connection_id)
                output_msg = f"堡垒机连接已断开: {connection_id}"
                result_data = {"connection_id": connection_id}
                
            elif operation == "execute":
                command = self._replace_variables(self.config.get("command", ""), inputs)
                timeout = self.config.get("timeout", 30)
                
                if not command:
                    raise ValueError("执行命令操作需要指定命令内容")
                
                status = bastion_service.get_connection_status(connection_id)
                if not status.get("authenticated"):
                    raise Exception("堡垒机未连接或未完成认证")
                
                channel = self._host_channel or bastion_service.get_channel(connection_id)
                if not channel:
                    raise Exception("无法获取可用通道")
                
                exec_result = bastion_service.execute_command(connection_id, command, timeout)
                if exec_result["success"]:
                    output_msg = f"命令执行成功:\n{exec_result['output']}"
                    result_data = exec_result
                    if self._host_channel:
                        result_data["executed_on_host"] = self._host_channel.target_host
                else:
                    raise Exception(exec_result.get("error", "命令执行失败"))
                    
            elif operation == "status":
                status = bastion_service.get_connection_status(connection_id)
                output_msg = f"连接状态: {status}"
                result_data = status
                
            else:
                raise ValueError(f"不支持的操作类型: {operation}")
            
            self.status = NodeStatus.SUCCESS
            self.result = NodeResult(
                status=NodeStatus.SUCCESS,
                output=output_msg,
                data=result_data
            )
            
        except ValueError as e:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=f"配置错误: {str(e)}"
            )
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error=f"堡垒机操作失败: {str(e)}"
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
    "minio": MinioNode,
    "bastion": BastionNode,
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
