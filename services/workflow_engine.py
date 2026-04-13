from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime
from core.logger import get_logger
from models.workflow_run import RunStatus, TriggerType
from services.workflow_service import WorkflowService
from abc import ABC, abstractmethod
import threading
import time

logger = get_logger(__name__)


class NodeExecutor(ABC):
    @abstractmethod
    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def node_type(self) -> str:
        pass


class StartNodeExecutor(NodeExecutor):
    @property
    def node_type(self) -> str:
        return "start"

    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "output": "工作流开始"}


class EndNodeExecutor(NodeExecutor):
    @property
    def node_type(self) -> str:
        return "end"

    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "output": "工作流结束"}


class ScriptNodeExecutor(NodeExecutor):
    def __init__(self, script_service=None, asset_service=None):
        self.script_service = script_service
        self.asset_service = asset_service

    @property
    def node_type(self) -> str:
        return "script"

    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        script_id = config.get("script_id")
        server_id = config.get("server_id")

        if not script_id:
            return {"success": False, "error": "未配置脚本ID"}

        if self.script_service and server_id:
            try:
                script = self.script_service.get_by_id(script_id)
                if script:
                    exec_log_id = self.script_service.execute(script, server_id)
                    return {"success": True, "output": f"脚本执行已提交, 执行记录ID: {exec_log_id}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": True, "output": f"模拟执行脚本 ID: {script_id}"}


class SSHNodeExecutor(NodeExecutor):
    def __init__(self, asset_service=None):
        self.asset_service = asset_service

    @property
    def node_type(self) -> str:
        return "ssh"

    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        server_id = config.get("server_id")
        command = config.get("command", "")

        if not server_id or not command:
            return {"success": False, "error": "未配置服务器或命令"}

        return {"success": True, "output": f"模拟SSH执行: {command[:50]}..."}


class ConditionNodeExecutor(NodeExecutor):
    @property
    def node_type(self) -> str:
        return "condition"

    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        condition_expr = config.get("expression", "true")
        try:
            result = eval(condition_expr, {"__builtins__": {}}, context)
            return {"success": True, "output": str(result), "branch": "true" if result else "false"}
        except Exception as e:
            return {"success": False, "error": f"条件表达式错误: {str(e)}"}


class DelayNodeExecutor(NodeExecutor):
    @property
    def node_type(self) -> str:
        return "delay"

    def execute(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        delay_seconds = config.get("delay_seconds", 1)
        time.sleep(delay_seconds)
        return {"success": True, "output": f"延迟 {delay_seconds} 秒完成"}


class WorkflowEngine:
    def __init__(self, workflow_service: WorkflowService, script_service=None, asset_service=None):
        self.workflow_service = workflow_service
        self.script_service = script_service
        self.asset_service = asset_service
        self.executors: Dict[str, NodeExecutor] = {}
        self._register_default_executors()
        self._running = False
        self._stop_flag = False

    def _register_default_executors(self):
        self.register_executor(StartNodeExecutor())
        self.register_executor(EndNodeExecutor())
        self.register_executor(ScriptNodeExecutor(self.script_service, self.asset_service))
        self.register_executor(SSHNodeExecutor(self.asset_service))
        self.register_executor(ConditionNodeExecutor())
        self.register_executor(DelayNodeExecutor())

    def register_executor(self, executor: NodeExecutor):
        self.executors[executor.node_type] = executor
        logger.info(f"注册节点执行器: {executor.node_type}")

    def build_dag(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, List[str]]:
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        node_keys = {n["node_key"] for n in nodes}
        for key in node_keys:
            in_degree[key] = 0

        for edge in edges:
            source = edge["source_node_key"]
            target = edge["target_node_key"]
            if source in node_keys and target in node_keys:
                graph[source].append(target)
                in_degree[target] += 1

        return graph, in_degree

    def topological_sort(self, graph: Dict[str, List[str]], in_degree: Dict[str, int]) -> List[str]:
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def execute_workflow(self, workflow_id: int, trigger_type: TriggerType = TriggerType.MANUAL) -> int:
        run_id = self.workflow_service.create_run(workflow_id, trigger_type)
        if not run_id:
            raise ValueError(f"无法创建工作流执行记录: workflow_id={workflow_id}")

        thread = threading.Thread(
            target=self._execute_workflow_async,
            args=(workflow_id, run_id)
        )
        thread.daemon = True
        thread.start()

        return run_id

    def _execute_workflow_async(self, workflow_id: int, run_id: int):
        self._running = True
        self._stop_flag = False

        try:
            self.workflow_service.update_run_status(
                run_id, RunStatus.RUNNING, start_time=datetime.now()
            )

            data = self.workflow_service.get_workflow_data(workflow_id)
            nodes = data["nodes"]
            edges = data["edges"]

            if not nodes:
                self.workflow_service.update_run_status(
                    run_id, RunStatus.SUCCESS, end_time=datetime.now()
                )
                logger.info(f"工作流 {workflow_id} 没有节点，执行完成")
                return

            graph, in_degree = self.build_dag(nodes, edges)
            execution_order = self.topological_sort(graph, in_degree.copy())

            if len(execution_order) != len(nodes):
                raise ValueError("工作流包含循环依赖，无法执行")

            node_map = {n["node_key"]: n for n in nodes}
            context: Dict[str, Any] = {}
            run_node_ids: Dict[str, int] = {}

            for node_key in execution_order:
                if self._stop_flag:
                    self.workflow_service.update_run_status(
                        run_id, RunStatus.CANCELLED, end_time=datetime.now()
                    )
                    logger.info(f"工作流 {workflow_id} 执行已取消")
                    return

                node = node_map.get(node_key)
                if not node:
                    continue

                run_node_id = self.workflow_service.create_run_node(run_id, node_key)
                run_node_ids[node_key] = run_node_id

                self.workflow_service.update_run_node(
                    run_node_id, RunStatus.RUNNING, start_time=datetime.now()
                )

                node_type = node["node_type"]
                config = node.get("config_json", {})

                executor = self.executors.get(node_type)
                if not executor:
                    self.workflow_service.update_run_node(
                        run_node_id, RunStatus.FAILED,
                        error=f"未知的节点类型: {node_type}",
                        end_time=datetime.now()
                    )
                    raise ValueError(f"未知的节点类型: {node_type}")

                try:
                    result = executor.execute(config, context)
                    if result.get("success"):
                        self.workflow_service.update_run_node(
                            run_node_id, RunStatus.SUCCESS,
                            output=result.get("output", ""),
                            end_time=datetime.now()
                        )
                        context[node_key] = result
                    else:
                        self.workflow_service.update_run_node(
                            run_node_id, RunStatus.FAILED,
                            error=result.get("error", "未知错误"),
                            end_time=datetime.now()
                        )
                        raise Exception(result.get("error", "节点执行失败"))

                except Exception as e:
                    self.workflow_service.update_run_node(
                        run_node_id, RunStatus.FAILED,
                        error=str(e),
                        end_time=datetime.now()
                    )
                    raise

            self.workflow_service.update_run_status(
                run_id, RunStatus.SUCCESS, end_time=datetime.now()
            )
            logger.info(f"工作流 {workflow_id} 执行完成, run_id={run_id}")

        except Exception as e:
            self.workflow_service.update_run_status(
                run_id, RunStatus.FAILED, end_time=datetime.now()
            )
            logger.error(f"工作流 {workflow_id} 执行失败: {str(e)}")

        finally:
            self._running = False

    def stop_execution(self):
        self._stop_flag = True
        logger.info("请求停止工作流执行")

    def is_running(self) -> bool:
        return self._running
