import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict
from core.logger import get_logger
from core.node_types import (
    BaseNode, NodeStatus, NodeResult,
    get_node_class, StartNode, EndNode, ConditionNode, ParallelNode, MergeNode, ScriptNode, CommandNode, MinioNode, BastionNode
)

logger = get_logger(__name__)


class WorkflowExecutor:
    def __init__(self, workflow_id: int, nodes: List[Dict], connections: List[Dict], 
                 script_service=None, dict_service=None, param_service=None, db=None):
        self.workflow_id = workflow_id
        self.nodes: Dict[int, BaseNode] = {}
        self.connections = connections
        self.adjacency: Dict[int, List[int]] = defaultdict(list)
        self.reverse_adjacency: Dict[int, List[int]] = defaultdict(list)
        self.node_outputs: Dict[int, NodeResult] = {}
        self.execution_callback: Optional[Callable] = None
        self.log_callback: Optional[Callable] = None
        self.is_running = False
        self.is_cancelled = False
        self._lock = threading.Lock()
        self.script_service = script_service
        self.dict_service = dict_service
        self.param_service = param_service
        self.db = db

        self._build_graph(nodes, connections)

    def _build_graph(self, nodes: List[Dict], connections: List[Dict]):
        for node_data in nodes:
            node_id = node_data["id"]
            node_type = node_data.get("node_type", "base")
            name = node_data.get("name", f"Node_{node_id}")
            config = node_data.get("config", {})

            if node_type == "script" and self.script_service:
                script_id = config.get("script_id")
                if script_id:
                    from models.script import Script
                    script = self.script_service.get_by_id(script_id)
                    if script:
                        config["script_content"] = script.content
                        config["script_language"] = script.language or "bash"
                        config["script_name"] = script.name

            node_class = get_node_class(node_type)
            node = node_class(node_id, name, config)
            
            if isinstance(node, (ScriptNode, CommandNode)):
                node.set_services(self.dict_service, self.param_service)
            elif isinstance(node, (MinioNode, BastionNode)):
                node.set_services(db=self.db)
            
            self.nodes[node_id] = node

        for conn in connections:
            source_id = conn.get("source_id") or conn.get("source")
            target_id = conn.get("target_id") or conn.get("target")
            if source_id is not None and target_id is not None:
                self.adjacency[source_id].append(target_id)
                self.reverse_adjacency[target_id].append(source_id)

    def set_callbacks(self, execution_callback: Callable = None, log_callback: Callable = None):
        self.execution_callback = execution_callback
        self.log_callback = log_callback

    def _emit_log(self, level: str, message: str, node_id: int = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "node_id": node_id
        }
        if self.log_callback:
            self.log_callback(log_entry)
        logger.info(f"[Workflow {self.workflow_id}] {message}")

    def _update_node_status(self, node_id: int, status: NodeStatus, result: NodeResult = None):
        with self._lock:
            if result:
                self.node_outputs[node_id] = result

            if self.execution_callback:
                self.execution_callback({
                    "node_id": node_id,
                    "status": status.value,
                    "output": result.output if result else "",
                    "error": result.error if result else ""
                })

    def _get_ready_nodes(self) -> List[int]:
        ready = []
        for node_id, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue

            predecessors = self.reverse_adjacency.get(node_id, [])
            all_done = True
            for pred_id in predecessors:
                pred_node = self.nodes.get(pred_id)
                if not pred_node or pred_node.status not in [NodeStatus.SUCCESS, NodeStatus.SKIPPED]:
                    all_done = False
                    break

            if all_done and predecessors:
                ready.append(node_id)

        for node_id, node in self.nodes.items():
            if isinstance(node, StartNode) and node.status == NodeStatus.PENDING:
                if node_id not in ready:
                    ready.append(node_id)

        return ready

    def _execute_node(self, node_id: int) -> NodeResult:
        if self.is_cancelled:
            return NodeResult(status=NodeStatus.SKIPPED, output="执行已取消")

        node = self.nodes[node_id]
        node.status = NodeStatus.RUNNING
        self._update_node_status(node_id, NodeStatus.RUNNING)
        
        log_message = f"开始执行节点: {node.name}"
        if isinstance(node, CommandNode):
            command = node.config.get("command", "")
            if command:
                log_message += f"，执行命令: {command}"
        elif isinstance(node, ScriptNode):
            script_name = node.config.get("script_name", "")
            script_language = node.config.get("script_language", "bash")
            if script_name:
                log_message += f"，执行脚本: {script_name} ({script_language})"
        self._emit_log("INFO", log_message, node_id)

        inputs = {}
        predecessors = self.reverse_adjacency.get(node_id, [])
        if predecessors:
            last_pred_id = predecessors[-1]
            if last_pred_id in self.node_outputs:
                pred_result = self.node_outputs[last_pred_id]
                inputs = {
                    "output": pred_result.output,
                    "data": pred_result.data,
                    "status": pred_result.status.value
                }

        try:
            result = node.execute(inputs)
            node.status = result.status
            node.result = result

            self._update_node_status(node_id, result.status, result)

            if result.status == NodeStatus.SUCCESS:
                output_msg = f"节点执行成功: {node.name}"
                if result.output:
                    output_msg += f"\n{result.output}"
                self._emit_log("INFO", output_msg, node_id)
            else:
                self._emit_log("ERROR", f"节点执行失败: {node.name} - {result.error}", node_id)

            return result

        except Exception as e:
            error_msg = str(e)
            node.status = NodeStatus.FAILED
            result = NodeResult(status=NodeStatus.FAILED, error=error_msg)
            node.result = result
            self._update_node_status(node_id, NodeStatus.FAILED, result)
            self._emit_log("ERROR", f"节点执行异常: {node.name} - {error_msg}", node_id)
            return result

    def execute(self, max_workers: int = 4) -> Dict[str, Any]:
        self.is_running = True
        self.is_cancelled = False
        start_time = datetime.now()

        self._emit_log("INFO", f"工作流开始执行，并行度: {max_workers}")

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                while self.is_running and not self.is_cancelled:
                    ready_nodes = self._get_ready_nodes()

                    if not ready_nodes:
                        all_done = all(
                            n.status in [NodeStatus.SUCCESS, NodeStatus.FAILED, NodeStatus.SKIPPED]
                            for n in self.nodes.values()
                        )
                        if all_done:
                            break

                        any_running = any(
                            n.status == NodeStatus.RUNNING for n in self.nodes.values()
                        )
                        if not any_running:
                            break

                        threading.Event().wait(0.1)
                        continue

                    futures = {}
                    for node_id in ready_nodes:
                        node = self.nodes[node_id]
                        node.status = NodeStatus.RUNNING
                        future = executor.submit(self._execute_node, node_id)
                        futures[future] = node_id

                    for future in as_completed(futures):
                        if self.is_cancelled:
                            break
                        node_id = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            self._emit_log("ERROR", f"节点执行异常: {node_id} - {str(e)}", node_id)

        except Exception as e:
            self._emit_log("ERROR", f"工作流执行异常: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "started_at": start_time.isoformat(),
                "finished_at": datetime.now().isoformat()
            }

        end_time = datetime.now()
        success_count = sum(1 for n in self.nodes.values() if n.status == NodeStatus.SUCCESS)
        failed_count = sum(1 for n in self.nodes.values() if n.status == NodeStatus.FAILED)

        final_status = "success" if failed_count == 0 else "failed"
        self._emit_log("INFO", f"工作流执行完成，状态: {final_status}，成功: {success_count}，失败: {failed_count}")

        self.is_running = False

        return {
            "status": final_status,
            "started_at": start_time.isoformat(),
            "finished_at": end_time.isoformat(),
            "success_count": success_count,
            "failed_count": failed_count,
            "node_results": {
                node_id: {
                    "status": node.status.value,
                    "output": node.result.output if node.result else "",
                    "error": node.result.error if node.result else ""
                }
                for node_id, node in self.nodes.items()
            }
        }

    def cancel(self):
        self.is_cancelled = True
        self.is_running = False
        self._emit_log("WARN", "工作流执行已取消")
