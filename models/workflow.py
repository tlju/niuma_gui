from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from models.base import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    graph_data = Column(JSON, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

    nodes = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    node_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    config = Column(JSON, nullable=True)
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True))

    workflow = relationship("Workflow", back_populates="nodes")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    status = Column(String(20), default="pending")
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    workflow = relationship("Workflow", back_populates="executions")
    node_executions = relationship("WorkflowNodeExecution", back_populates="execution", cascade="all, delete-orphan")


class WorkflowNodeExecution(Base):
    __tablename__ = "workflow_node_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("workflow_executions.id"), nullable=False)
    node_id = Column(Integer, ForeignKey("workflow_nodes.id"))
    node_name = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    execution = relationship("WorkflowExecution", back_populates="node_executions")
