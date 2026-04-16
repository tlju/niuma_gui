import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.workflow import Workflow, WorkflowNode, WorkflowExecution, WorkflowNodeExecution
from models.audit_log import AuditLog
from core.logger import get_logger
from core.workflow_engine import WorkflowExecutor
from core.node_types import NodeStatus
from core.utils import get_local_now

logger = get_logger(__name__)


class WorkflowService:
    def __init__(self, db: Session, script_service=None, dict_service=None, param_service=None):
        self.db = db
        self.script_service = script_service
        self.dict_service = dict_service
        self.param_service = param_service

    def get_all(self) -> List[Workflow]:
        return self.db.query(Workflow).filter(
            Workflow.is_active == True
        ).order_by(desc(Workflow.updated_at)).all()

    def get_by_id(self, workflow_id: int) -> Optional[Workflow]:
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def create(self, name: str, description: str = "", user_id: int = None, graph_data: Dict = None) -> Workflow:
        workflow = Workflow(
            name=name,
            description=description,
            created_by=user_id,
            graph_data=graph_data or {"nodes": [], "connections": []},
            created_at=get_local_now()
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"创建工作流: {name}, ID: {workflow.id}")

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="create",
                resource_type="workflow",
                resource_id=workflow.id,
                details=f"创建工作流: {name}",
                created_at=get_local_now()
            )
            self.db.add(audit)
            self.db.commit()

        return workflow

    def update(self, workflow_id: int, user_id: int = None, **kwargs) -> Optional[Workflow]:
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return None

        for key, value in kwargs.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)

        workflow.updated_at = get_local_now()
        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"更新工作流: {workflow.name}, ID: {workflow_id}")

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="update",
                resource_type="workflow",
                resource_id=workflow_id,
                details=f"更新工作流: {workflow.name}",
                created_at=get_local_now()
            )
            self.db.add(audit)
            self.db.commit()

        return workflow

    def delete(self, workflow_id: int, user_id: int = None) -> bool:
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return False

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="delete",
                resource_type="workflow",
                resource_id=workflow_id,
                details=f"删除工作流: {workflow.name}",
                created_at=get_local_now()
            )
            self.db.add(audit)

        workflow.is_active = False
        self.db.commit()
        logger.info(f"删除工作流: {workflow.name}, ID: {workflow_id}")
        return True

    def save_graph(self, workflow_id: int, nodes: List[Dict], connections: List[Dict], user_id: int = None) -> Optional[Workflow]:
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return None

        graph_data = {"nodes": nodes, "connections": connections}
        workflow.graph_data = graph_data
        workflow.updated_at = get_local_now()

        self.db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).delete()

        for node_data in nodes:
            node = WorkflowNode(
                workflow_id=workflow_id,
                node_type=node_data.get("node_type", "base"),
                name=node_data.get("name", f"Node_{node_data['id']}"),
                config=node_data.get("config", {}),
                position_x=node_data.get("x", 0),
                position_y=node_data.get("y", 0),
                created_at=get_local_now()
            )
            self.db.add(node)

        self.db.commit()
        self.db.refresh(workflow)
        logger.info(f"保存工作流图形: {workflow.name}, 节点数: {len(nodes)}")

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="update",
                resource_type="workflow",
                resource_id=workflow_id,
                details=f"保存工作流图形: {workflow.name}",
                created_at=get_local_now()
            )
            self.db.add(audit)
            self.db.commit()

        return workflow

    def get_executions(self, workflow_id: int = None, limit: int = 50) -> List[WorkflowExecution]:
        query = self.db.query(WorkflowExecution)
        if workflow_id:
            query = query.filter(WorkflowExecution.workflow_id == workflow_id)
        return query.order_by(desc(WorkflowExecution.started_at)).limit(limit).all()

    def get_execution_by_id(self, execution_id: int) -> Optional[WorkflowExecution]:
        return self.db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()

    def create_execution(self, workflow_id: int) -> WorkflowExecution:
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status="pending",
            started_at=get_local_now()
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def update_execution(self, execution_id: int, **kwargs) -> Optional[WorkflowExecution]:
        execution = self.get_execution_by_id(execution_id)
        if not execution:
            return None

        for key, value in kwargs.items():
            if hasattr(execution, key):
                setattr(execution, key, value)

        self.db.commit()
        self.db.refresh(execution)
        return execution

    def create_node_execution(self, execution_id: int, node_id: int, node_name: str) -> WorkflowNodeExecution:
        node_exec = WorkflowNodeExecution(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            status="pending",
            started_at=get_local_now()
        )
        self.db.add(node_exec)
        self.db.commit()
        self.db.refresh(node_exec)
        return node_exec

    def update_node_execution(self, node_exec_id: int, **kwargs) -> Optional[WorkflowNodeExecution]:
        node_exec = self.db.query(WorkflowNodeExecution).filter(
            WorkflowNodeExecution.id == node_exec_id
        ).first()
        if not node_exec:
            return None

        for key, value in kwargs.items():
            if hasattr(node_exec, key):
                setattr(node_exec, key, value)

        self.db.commit()
        self.db.refresh(node_exec)
        return node_exec

    def execute_workflow(self, workflow_id: int, user_id: int = None, max_workers: int = 4,
                         execution_callback=None, log_callback=None) -> Dict[str, Any]:
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return {"status": "failed", "error": "工作流不存在"}

        graph_data = workflow.graph_data or {"nodes": [], "connections": []}
        nodes = graph_data.get("nodes", [])
        connections = graph_data.get("connections", [])

        if not nodes:
            return {"status": "failed", "error": "工作流没有节点"}

        execution = self.create_execution(workflow_id)

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="execute",
                resource_type="workflow",
                resource_id=workflow_id,
                details=f"执行工作流: {workflow.name}",
                created_at=get_local_now()
            )
            self.db.add(audit)
            self.db.commit()

        executor = WorkflowExecutor(workflow_id, nodes, connections, self.script_service, 
                                    self.dict_service, self.param_service)

        node_exec_map = {}
        for node_data in nodes:
            node_exec = self.create_node_execution(
                execution.id,
                node_data["id"],
                node_data.get("name", f"Node_{node_data['id']}")
            )
            node_exec_map[node_data["id"]] = node_exec

        execution_logs = []

        def db_execution_callback(update):
            node_id = update.get("node_id")
            status = update.get("status")
            output = update.get("output", "")
            error = update.get("error", "")

            if node_id in node_exec_map:
                node_exec = node_exec_map[node_id]
                self.update_node_execution(
                    node_exec.id,
                    status=status,
                    output=output,
                    error_message=error,
                    finished_at=get_local_now() if status in ["success", "failed", "skipped"] else None
                )

            if execution_callback:
                execution_callback(update)

        def db_log_callback(log_entry):
            logger.info(f"[Workflow {workflow_id}] {log_entry['message']}")
            
            execution_logs.append(log_entry)

            if log_callback:
                log_callback(log_entry)

        executor.set_callbacks(db_execution_callback, db_log_callback)

        result = executor.execute(max_workers=max_workers)

        self.update_execution(
            execution.id,
            status=result["status"],
            finished_at=get_local_now(),
            result=result.get("node_results"),
            error_message=result.get("error"),
            logs=execution_logs
        )

        return result
