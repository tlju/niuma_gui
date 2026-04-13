from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base
from models.workflow_run import RunStatus


class WorkflowRunNode(Base):
    __tablename__ = "workflow_run_nodes"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    node_key = Column(String(36), nullable=False)
    status = Column(Enum(RunStatus), default=RunStatus.PENDING)
    output = Column(Text)
    error = Column(Text)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))

    run = relationship("WorkflowRun", back_populates="node_runs")
