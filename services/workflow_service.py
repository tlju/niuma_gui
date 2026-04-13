from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.workflow import Workflow, WorkflowStatus
from models.workflow_node import WorkflowNode
from models.workflow_edge import WorkflowEdge
from models.workflow_run import WorkflowRun, RunStatus, TriggerType
from models.workflow_run_node import WorkflowRunNode
from models.audit_log import AuditLog
from typing import List, Optional, Dict, Any
from core.logger import get_logger
import uuid
import json

logger = get_logger(__name__)


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[int]:
        workflow = Workflow(
            name=name,
            description=description,
            status=WorkflowStatus.DRAFT
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="create",
                resource_type="workflow",
                resource_id=workflow.id
            )
            self.db.add(audit)
            self.db.commit()

        logger.info(f"创建工作流: {name}, ID: {workflow.id}")
        return workflow.id

    def get_all_workflows(self) -> List[Workflow]:
        return self.db.query(Workflow).order_by(Workflow.updated_at.desc()).all()

    def get_workflow_by_id(self, workflow_id: int) -> Optional[Workflow]:
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def update_workflow(
        self,
        workflow_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
        user_id: Optional[int] = None
    ) -> bool:
        workflow = self.get_workflow_by_id(workflow_id)
        if not workflow:
            return False

        if name is not None:
            workflow.name = name
        if description is not None:
            workflow.description = description
        if status is not None:
            workflow.status = status

        self.db.commit()

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="update",
                resource_type="workflow",
                resource_id=workflow_id
            )
            self.db.add(audit)
            self.db.commit()

        logger.info(f"更新工作流: {workflow_id}")
        return True

    def delete_workflow(self, workflow_id: int, user_id: Optional[int] = None) -> bool:
        workflow = self.get_workflow_by_id(workflow_id)
        if not workflow:
            return False

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="delete",
                resource_type="workflow",
                resource_id=workflow_id
            )
            self.db.add(audit)

        self.db.delete(workflow)
        self.db.commit()
        logger.info(f"删除工作流: {workflow_id}")
        return True

    def save_workflow_data(
        self,
        workflow_id: int,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> bool:
        workflow = self.get_workflow_by_id(workflow_id)
        if not workflow:
            return False

        self.db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).delete()
        self.db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow_id).delete()

        for node_data in nodes:
            node = WorkflowNode(
                workflow_id=workflow_id,
                node_key=node_data.get("node_key", str(uuid.uuid4())),
                node_type=node_data.get("node_type", "unknown"),
                node_name=node_data.get("node_name", "未命名节点"),
                pos_x=node_data.get("pos_x", 0),
                pos_y=node_data.get("pos_y", 0),
                config_json=node_data.get("config_json", {})
            )
            self.db.add(node)

        for edge_data in edges:
            edge = WorkflowEdge(
                workflow_id=workflow_id,
                source_node_key=edge_data.get("source_node_key"),
                target_node_key=edge_data.get("target_node_key"),
                source_port=edge_data.get("source_port", 0),
                target_port=edge_data.get("target_port", 0),
                condition_json=edge_data.get("condition_json", {})
            )
            self.db.add(edge)

        self.db.commit()

        if user_id:
            audit = AuditLog(
                user_id=user_id,
                action_type="update",
                resource_type="workflow_data",
                resource_id=workflow_id
            )
            self.db.add(audit)
            self.db.commit()

        logger.info(f"保存工作流数据: {workflow_id}, 节点数: {len(nodes)}, 连线数: {len(edges)}")
        return True

    def get_workflow_data(self, workflow_id: int) -> Dict[str, Any]:
        workflow = self.get_workflow_by_id(workflow_id)
        if not workflow:
            return {"workflow": None, "nodes": [], "edges": []}

        nodes = self.db.query(WorkflowNode).filter(
            WorkflowNode.workflow_id == workflow_id
        ).all()

        edges = self.db.query(WorkflowEdge).filter(
            WorkflowEdge.workflow_id == workflow_id
        ).all()

        return {
            "workflow": workflow,
            "nodes": [
                {
                    "id": n.id,
                    "node_key": n.node_key,
                    "node_type": n.node_type,
                    "node_name": n.node_name,
                    "pos_x": n.pos_x,
                    "pos_y": n.pos_y,
                    "config_json": n.config_json or {}
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_node_key": e.source_node_key,
                    "target_node_key": e.target_node_key,
                    "source_port": e.source_port,
                    "target_port": e.target_port,
                    "condition_json": e.condition_json or {}
                }
                for e in edges
            ]
        }

    def create_run(
        self,
        workflow_id: int,
        trigger_type: TriggerType = TriggerType.MANUAL
    ) -> Optional[int]:
        run = WorkflowRun(
            workflow_id=workflow_id,
            status=RunStatus.PENDING,
            trigger_type=trigger_type
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        logger.info(f"创建工作流执行记录: workflow_id={workflow_id}, run_id={run.id}")
        return run.id

    def get_run_by_id(self, run_id: int) -> Optional[WorkflowRun]:
        return self.db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()

    def get_runs_by_workflow(self, workflow_id: int) -> List[WorkflowRun]:
        return self.db.query(WorkflowRun).filter(
            WorkflowRun.workflow_id == workflow_id
        ).order_by(WorkflowRun.created_at.desc()).all()

    def update_run_status(
        self,
        run_id: int,
        status: RunStatus,
        start_time=None,
        end_time=None
    ) -> bool:
        run = self.get_run_by_id(run_id)
        if not run:
            return False

        run.status = status
        if start_time is not None:
            run.start_time = start_time
        if end_time is not None:
            run.end_time = end_time

        self.db.commit()
        logger.info(f"更新执行记录状态: run_id={run_id}, status={status}")
        return True

    def create_run_node(
        self,
        run_id: int,
        node_key: str
    ) -> Optional[int]:
        run_node = WorkflowRunNode(
            run_id=run_id,
            node_key=node_key,
            status=RunStatus.PENDING
        )
        self.db.add(run_node)
        self.db.commit()
        self.db.refresh(run_node)
        return run_node.id

    def update_run_node(
        self,
        run_node_id: int,
        status: Optional[RunStatus] = None,
        output: Optional[str] = None,
        error: Optional[str] = None,
        start_time=None,
        end_time=None
    ) -> bool:
        run_node = self.db.query(WorkflowRunNode).filter(
            WorkflowRunNode.id == run_node_id
        ).first()
        if not run_node:
            return False

        if status is not None:
            run_node.status = status
        if output is not None:
            run_node.output = output
        if error is not None:
            run_node.error = error
        if start_time is not None:
            run_node.start_time = start_time
        if end_time is not None:
            run_node.end_time = end_time

        self.db.commit()
        return True

    def get_run_nodes(self, run_id: int) -> List[WorkflowRunNode]:
        return self.db.query(WorkflowRunNode).filter(
            WorkflowRunNode.run_id == run_id
        ).all()

    def get_node_by_key(self, workflow_id: int, node_key: str) -> Optional[WorkflowNode]:
        return self.db.query(WorkflowNode).filter(
            and_(
                WorkflowNode.workflow_id == workflow_id,
                WorkflowNode.node_key == node_key
            )
        ).first()

    def get_edges_by_node(self, workflow_id: int, node_key: str) -> List[WorkflowEdge]:
        return self.db.query(WorkflowEdge).filter(
            and_(
                WorkflowEdge.workflow_id == workflow_id,
                WorkflowEdge.source_node_key == node_key
            )
        ).all()

    def get_incoming_edges(self, workflow_id: int, node_key: str) -> List[WorkflowEdge]:
        return self.db.query(WorkflowEdge).filter(
            and_(
                WorkflowEdge.workflow_id == workflow_id,
                WorkflowEdge.target_node_key == node_key
            )
        ).all()
