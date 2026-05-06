from __future__ import annotations

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import desc
from models.workflow import Workflow, WorkflowNode, WorkflowExecution, WorkflowNodeExecution
from services.audit_mixin import AuditMixin
from core.logger import get_logger
from core.workflow_engine import WorkflowExecutor
from core.node_types import NodeStatus
from core.utils import get_local_now
from core.database import get_db, get_thread_db

logger = get_logger(__name__)


class WorkflowService(AuditMixin):
    UPDATABLE_FIELDS = frozenset({
        "name", "description", "graph_data"
    })

    EXECUTION_UPDATABLE_FIELDS = frozenset({
        "status", "finished_at", "result", "error_message", "logs"
    })

    NODE_EXECUTION_UPDATABLE_FIELDS = frozenset({
        "status", "output", "error_message", "finished_at"
    })

    def __init__(self, script_service=None, dict_service=None, param_service=None, bastion_manager=None):
        self.script_service = script_service
        self.dict_service = dict_service
        self.param_service = param_service
        self.bastion_manager = bastion_manager

    def get_all(self) -> List[Workflow]:
        with get_db() as db:
            return db.query(Workflow).filter(
                Workflow.is_active == True
            ).order_by(desc(Workflow.updated_at)).all()

    def get_by_id(self, workflow_id: int) -> Optional[Workflow]:
        with get_db() as db:
            return db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def create(self, name: str, description: str = "", user_id: int = None, graph_data: Dict = None) -> Workflow:
        with get_db() as db:
            workflow = Workflow(
                name=name,
                description=description,
                created_by=user_id,
                graph_data=graph_data or {"nodes": [], "connections": []},
                created_at=get_local_now()
            )
            db.add(workflow)
            db.commit()
            db.refresh(workflow)
            logger.info(f"创建工作流: {name}, ID: {workflow.id}")

        self.log_create(
            user_id=user_id,
            resource_type="workflow",
            resource_id=workflow.id,
            resource_name=name
        )

        return workflow

    def update(self, workflow_id: int, user_id: int = None, **kwargs) -> Optional[Workflow]:
        with get_db() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not workflow:
                return None

            for key, value in kwargs.items():
                if key in self.UPDATABLE_FIELDS:
                    setattr(workflow, key, value)

            workflow.updated_at = get_local_now()
            try:
                db.commit()
                db.refresh(workflow)
            except Exception as e:
                db.rollback()
                logger.error(f"更新工作流失败: {e}")
                raise
        logger.info(f"更新工作流: {workflow.name}, ID: {workflow_id}")

        self.log_update(
            user_id=user_id,
            resource_type="workflow",
            resource_id=workflow_id,
            resource_name=workflow.name
        )

        return workflow

    def delete(self, workflow_id: int, user_id: int = None) -> bool:
        with get_db() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not workflow:
                return False

            self.log_delete(
                user_id=user_id,
                resource_type="workflow",
                resource_id=workflow_id,
                resource_name=workflow.name
            )

            workflow.is_active = False
            db.commit()
            logger.info(f"删除工作流: {workflow.name}, ID: {workflow_id}")
        return True

    def save_graph(self, workflow_id: int, nodes: List[Dict], connections: List[Dict], user_id: int = None) -> Optional[Workflow]:
        with get_db() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not workflow:
                return None

            graph_data = {"nodes": nodes, "connections": connections}
            workflow.graph_data = graph_data
            workflow.updated_at = get_local_now()

            db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).delete()

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
                db.add(node)

            db.commit()
            db.refresh(workflow)
            logger.info(f"保存工作流图形: {workflow.name}, 节点数: {len(nodes)}")

        self.log_audit(
            user_id=user_id,
            action_type="update",
            resource_type="workflow",
            resource_id=workflow_id,
            details=f"保存工作流图形: {workflow.name}"
        )

        return workflow

    def get_executions(self, workflow_id: int = None, limit: int = 50) -> List[WorkflowExecution]:
        with get_db() as db:
            query = db.query(WorkflowExecution)
            if workflow_id:
                query = query.filter(WorkflowExecution.workflow_id == workflow_id)
            return query.order_by(desc(WorkflowExecution.started_at)).limit(limit).all()

    def get_execution_by_id(self, execution_id: int) -> Optional[WorkflowExecution]:
        with get_db() as db:
            return db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()

    def create_execution(self, workflow_id: int) -> WorkflowExecution:
        with get_db() as db:
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                status="pending",
                started_at=get_local_now()
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
            return execution

    def update_execution(self, execution_id: int, **kwargs) -> Optional[WorkflowExecution]:
        with get_db() as db:
            execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
            if not execution:
                return None

            for key, value in kwargs.items():
                if key in self.EXECUTION_UPDATABLE_FIELDS:
                    setattr(execution, key, value)

            db.commit()
            db.refresh(execution)
            return execution

    def create_node_execution(self, execution_id: int, node_id: int, node_name: str) -> WorkflowNodeExecution:
        with get_db() as db:
            node_exec = WorkflowNodeExecution(
                execution_id=execution_id,
                node_id=node_id,
                node_name=node_name,
                status="pending",
                started_at=get_local_now()
            )
            db.add(node_exec)
            db.commit()
            db.refresh(node_exec)
            return node_exec

    def update_node_execution(self, node_exec_id: int, **kwargs) -> Optional[WorkflowNodeExecution]:
        with get_db() as db:
            node_exec = db.query(WorkflowNodeExecution).filter(
                WorkflowNodeExecution.id == node_exec_id
            ).first()
            if not node_exec:
                return None

            for key, value in kwargs.items():
                if key in self.NODE_EXECUTION_UPDATABLE_FIELDS:
                    setattr(node_exec, key, value)

            db.commit()
            db.refresh(node_exec)
            return node_exec

    def delete_execution(self, execution_id: int, user_id: int = None) -> bool:
        with get_db() as db:
            execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
            if not execution:
                return False

            self.log_delete(
                user_id=user_id,
                resource_type="workflow_execution",
                resource_id=execution_id,
                details=f"删除工作流执行记录: #{execution_id}"
            )

            db.delete(execution)
            db.commit()
            logger.info(f"删除工作流执行记录: #{execution_id}")
        return True

    def delete_executions(self, execution_ids: List[int], user_id: int = None) -> int:
        deleted_count = 0
        for execution_id in execution_ids:
            if self.delete_execution(execution_id, user_id):
                deleted_count += 1
        return deleted_count

    def export_workflow(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return None

        export_data = {
            "name": workflow.name,
            "description": workflow.description or "",
            "graph_data": workflow.graph_data or {"nodes": [], "connections": []},
            "export_version": "1.0"
        }

        logger.info(f"导出工作流: {workflow.name}, ID: {workflow_id}")
        return export_data

    def import_workflow(self, data: Dict[str, Any], user_id: int = None) -> Optional[Workflow]:
        if not data:
            return None

        name = data.get("name", "导入的工作流")
        description = data.get("description", "")
        graph_data = data.get("graph_data", {"nodes": [], "connections": []})

        name = self._generate_unique_name(name)

        workflow = self.create(
            name=name,
            description=description,
            user_id=user_id,
            graph_data=graph_data
        )

        self.log_audit(
            user_id=user_id,
            action_type="import",
            resource_type="workflow",
            resource_id=workflow.id,
            details=f"导入工作流: {name}"
        )

        logger.info(f"导入工作流: {name}, ID: {workflow.id}")
        return workflow

    def _generate_unique_name(self, base_name: str) -> str:
        with get_db() as db:
            existing_names = set(
                w.name for w in db.query(Workflow.name).filter(
                    Workflow.is_active == True
                ).all()
            )

        if base_name not in existing_names:
            return base_name

        counter = 1
        while True:
            new_name = f"{base_name} ({counter})"
            if new_name not in existing_names:
                return new_name
            counter += 1

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

        self.log_execute(
            user_id=user_id,
            resource_type="workflow",
            resource_id=workflow_id,
            resource_name=workflow.name
        )

        executor = WorkflowExecutor(
            workflow_id, nodes, connections,
            self.script_service, self.dict_service,
            self.param_service, self.bastion_manager
        )

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
                with get_thread_db() as thread_db:
                    try:
                        node_exec_db = thread_db.query(WorkflowNodeExecution).filter(
                            WorkflowNodeExecution.id == node_exec.id
                        ).first()
                        if node_exec_db:
                            node_exec_db.status = status
                            node_exec_db.output = output
                            node_exec_db.error_message = error
                            if status in ["success", "failed", "skipped"]:
                                node_exec_db.finished_at = get_local_now()
                            thread_db.commit()
                    except Exception as e:
                        logger.error(f"更新节点执行状态失败: {e}")
                        thread_db.rollback()

            if execution_callback:
                execution_callback(update)

        def db_log_callback(log_entry):
            logger.debug(f"[Workflow {workflow_id}] {log_entry['message']}")

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
