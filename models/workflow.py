from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from models.base import Base

class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    definition = Column(Text)  # JSON 格式的工作流定义
    is_active = Column(String(10), default="Y")
    created_by = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("workflow_templates.id"))
    name = Column(String(100))
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    variables = Column(Text)  # JSON 格式
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, ForeignKey("workflow_instances.id"))
    step_name = Column(String(100))
    status = Column(String(20))
    output = Column(Text)
    error = Column(Text)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
