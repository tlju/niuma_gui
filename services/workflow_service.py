from sqlalchemy.orm import Session
from models.workflow import WorkflowTemplate, WorkflowInstance, WorkflowExecution
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from core.logger import get_logger

logger = get_logger(__name__)


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def create_template(self, name: str, description: str = None,
                        definition: Dict = None, created_by: int = None,
                        is_active: str = "Y") -> WorkflowTemplate:
        template = WorkflowTemplate(
            name=name,
            description=description,
            definition=json.dumps(definition) if definition else "{}",
            created_by=created_by,
            is_active=is_active
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        logger.info(f"创建工作流模板: {name}")
        return template

    def get_templates(self, skip: int = 0, limit: int = 100) -> List[WorkflowTemplate]:
        return self.db.query(WorkflowTemplate).offset(skip).limit(limit).all()

    def get_template(self, template_id: int) -> Optional[WorkflowTemplate]:
        return self.db.query(WorkflowTemplate).filter(
            WorkflowTemplate.id == template_id
        ).first()

    def update_template(self, template_id: int, **kwargs) -> Optional[WorkflowTemplate]:
        template = self.get_template(template_id)
        if not template:
            return None

        if 'definition' in kwargs and isinstance(kwargs['definition'], dict):
            kwargs['definition'] = json.dumps(kwargs['definition'])

        for key, value in kwargs.items():
            if value is not None and hasattr(template, key):
                setattr(template, key, value)

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"更新工作流模板: {template.name}")
        return template

    def delete_template(self, template_id: int) -> bool:
        template = self.get_template(template_id)
        if template:
            self.db.query(WorkflowInstance).filter(
                WorkflowInstance.template_id == template_id
            ).delete()
            self.db.delete(template)
            self.db.commit()
            logger.info(f"删除工作流模板: {template.name}")
            return True
        return False

    def create_instance(self, template_id: int, name: str = None,
                        variables: Dict = None) -> WorkflowInstance:
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")

        instance = WorkflowInstance(
            template_id=template_id,
            name=name or template.name,
            variables=json.dumps(variables) if variables else "{}"
        )
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"创建工作流实例: {instance.name}")
        return instance

    def get_instances(self, template_id: int = None, status: str = None,
                      skip: int = 0, limit: int = 100) -> List[WorkflowInstance]:
        query = self.db.query(WorkflowInstance)
        if template_id:
            query = query.filter(WorkflowInstance.template_id == template_id)
        if status:
            query = query.filter(WorkflowInstance.status == status)
        return query.order_by(WorkflowInstance.id.desc()).offset(skip).limit(limit).all()

    def get_instance(self, instance_id: int) -> Optional[WorkflowInstance]:
        return self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == instance_id
        ).first()

    def start_instance(self, instance_id: int) -> WorkflowInstance:
        instance = self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"实例 {instance_id} 不存在")

        if instance.status != "pending":
            raise ValueError("实例已启动")

        instance.status = "running"
        instance.started_at = datetime.now()
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"启动工作流实例: {instance.name}")
        return instance

    def complete_instance(self, instance_id: int) -> WorkflowInstance:
        instance = self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"实例 {instance_id} 不存在")

        instance.status = "completed"
        instance.completed_at = datetime.now()
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"完成工作流实例: {instance.name}")
        return instance

    def fail_instance(self, instance_id: int) -> WorkflowInstance:
        instance = self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"实例 {instance_id} 不存在")

        instance.status = "failed"
        instance.completed_at = datetime.now()
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"工作流实例失败: {instance.name}")
        return instance

    def create_execution(self, instance_id: int, step_name: str,
                         status: str = "pending", output: str = None,
                         error: str = None) -> WorkflowExecution:
        execution = WorkflowExecution(
            instance_id=instance_id,
            step_name=step_name,
            status=status,
            output=output,
            error=error
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        logger.info(f"创建工作流执行记录: {step_name}")
        return execution

    def get_executions(self, instance_id: int) -> List[WorkflowExecution]:
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.instance_id == instance_id
        ).order_by(WorkflowExecution.id).all()

    def get_template_definition(self, template_id: int) -> Dict:
        template = self.get_template(template_id)
        if template and template.definition:
            return json.loads(template.definition)
        return {}

    def get_instance_variables(self, instance_id: int) -> Dict:
        instance = self.get_instance(instance_id)
        if instance and instance.variables:
            return json.loads(instance.variables)
        return {}
