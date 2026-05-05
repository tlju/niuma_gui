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
from core.utils import replace_variables, get_python_executable, get_subprocess_kwargs

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
        return replace_variables(content, self.dict_service, self.param_service)

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
            
            if inputs.get("execution_environment") == "remote":
                bastion_manager = inputs.get("bastion_manager")
                if not bastion_manager:
                    self.status = NodeStatus.FAILED
                    self.result = NodeResult(
                        status=NodeStatus.FAILED,
                        error="远程执行环境但堡垒机管理器不可用"
                    )
                    return self.result
                
                try:
                    exec_result = bastion_manager.execute_command(command, timeout)
                    if exec_result.get("success"):
                        self.status = NodeStatus.SUCCESS
                        self.result = NodeResult(
                            status=NodeStatus.SUCCESS,
                            output=exec_result.get("output", ""),
                            data={"return_code": 0, "target_host": inputs.get("target_host")}
                        )
                    else:
                        self.status = NodeStatus.FAILED
                        self.result = NodeResult(
                            status=NodeStatus.FAILED,
                            output=exec_result.get("output", ""),
                            error=exec_result.get("error", "远程命令执行失败")
                        )
                except Exception as e:
                    self.status = NodeStatus.FAILED
                    self.result = NodeResult(
                        status=NodeStatus.FAILED,
                        error=f"远程命令执行异常: {str(e)}"
                    )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=working_dir,
                    **get_subprocess_kwargs()
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
        return replace_variables(content, self.dict_service, self.param_service)

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
        temp_file = None
        command = self._build_command_for_language(script_content, script_language)
        if script_language in ("python", "sql"):
            temp_file = command.split()[-1] if command else None

        if inputs.get("output"):
            command = command.replace("${input}", str(inputs.get("output", "")))

        try:
            self.status = NodeStatus.RUNNING
            
            if inputs.get("execution_environment") == "remote":
                bastion_manager = inputs.get("bastion_manager")
                if not bastion_manager:
                    self.status = NodeStatus.FAILED
                    self.result = NodeResult(
                        status=NodeStatus.FAILED,
                        error="远程执行环境但堡垒机管理器不可用"
                    )
                    return self.result
                
                if script_language != "bash":
                    self.status = NodeStatus.FAILED
                    self.result = NodeResult(
                        status=NodeStatus.FAILED,
                        error=f"远程执行仅支持Bash脚本，当前脚本语言: {script_language}"
                    )
                    return self.result
                
                try:
                    exec_result = bastion_manager.execute_command(command, timeout)
                    if exec_result.get("success"):
                        self.status = NodeStatus.SUCCESS
                        self.result = NodeResult(
                            status=NodeStatus.SUCCESS,
                            output=exec_result.get("output", ""),
                            data={"return_code": 0, "script_name": script_name, "script_language": script_language, "target_host": inputs.get("target_host")}
                        )
                    else:
                        self.status = NodeStatus.FAILED
                        self.result = NodeResult(
                            status=NodeStatus.FAILED,
                            output=exec_result.get("output", ""),
                            error=exec_result.get("error", "远程脚本执行失败")
                        )
                except Exception as e:
                    self.status = NodeStatus.FAILED
                    self.result = NodeResult(
                        status=NodeStatus.FAILED,
                        error=f"远程脚本执行异常: {str(e)}"
                    )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=working_dir,
                    **get_subprocess_kwargs()
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
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass

        return self.result

    def _build_command_for_language(self, script_content: str, language: str) -> str:
        if language == "python":
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                temp_file = f.name
            python_exec = get_python_executable()
            return f'"{python_exec}" {temp_file}'
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


class RemoteExecutionNode(BaseNode):
    node_type = "remote_execution"
    category = "environment"
    display_name = "远程执行"
    description = "切换到远程执行环境，此节点之后的所有动作节点将在远程主机执行，直至遇到本机执行节点"
    input_ports = 1
    output_ports = 1

    def __init__(self, node_id: int, name: str, config: Dict[str, Any] = None):
        super().__init__(node_id, name, config)
        self.db = None
        self.bastion_manager = None

    def set_services(self, db=None, bastion_manager=None, **kwargs):
        self.db = db
        self.bastion_manager = bastion_manager

    def get_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_host": {
                    "type": "string",
                    "title": "目标主机地址",
                    "description": "选择或输入目标主机IP地址。可从下拉菜单选择已连接的主机，或手动输入IP地址",
                    "dynamicEnum": "connected_hosts",
                    "allowManualInput": True,
                    "placeholder": "选择或输入目标主机IP"
                }
            },
            "required": ["target_host"]
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
                        logger.debug(f"参数变量替换成功: @{var_path} -> {param.param_value}")
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

        target_host = self.config.get("target_host", "")
        target_host = self._replace_variables(target_host, inputs)
        
        if not target_host:
            self.status = NodeStatus.FAILED
            self.result = NodeResult(
                status=NodeStatus.FAILED,
                error="未指定目标主机地址"
            )
            return self.result

        try:
            self.status = NodeStatus.RUNNING
            bastion_service = BastionService(db=self.db)
            
            connection_id = "default"
            
            status = bastion_service.get_connection_status(connection_id)
            if not status.get("authenticated"):
                raise Exception("堡垒机未连接或未完成认证，请先在主界面连接堡垒机")
            
            channel = bastion_service.connect_to_host(
                connection_id=connection_id,
                host=target_host,
                username=None,
                password=None,
                timeout=30
            )
            
            if channel:
                output_msg = f"已切换到远程执行环境，目标主机: {target_host}"
                result_data = {
                    "target_host": target_host,
                    "channel_id": channel.channel_id,
                    "connected": True,
                    "execution_environment": "remote"
                }
                
                self.status = NodeStatus.SUCCESS
                self.result = NodeResult(
                    status=NodeStatus.SUCCESS,
                    output=output_msg,
                    data=result_data
                )
            else:
                raise Exception(f"连接目标主机 {target_host} 失败")
            
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
                error=f"远程执行环境切换失败: {str(e)}"
            )
        
        return self.result


class LocalExecutionNode(BaseNode):
    node_type = "local_execution"
    category = "environment"
    display_name = "本机执行"
    description = "切换到本地执行环境，此节点之后的所有节点将在本地环境执行"
    input_ports = 1
    output_ports = 1

    def execute(self, inputs: Dict[str, Any] = None) -> NodeResult:
        self.status = NodeStatus.SUCCESS
        self.result = NodeResult(
            status=NodeStatus.SUCCESS, 
            output="已切换到本地执行环境",
            data={"execution_environment": "local"}
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
    "remote_execution": RemoteExecutionNode,
    "local_execution": LocalExecutionNode,
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
