from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from models.base import Base


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    source_node_key = Column(String(36), nullable=False)
    target_node_key = Column(String(36), nullable=False)
    source_port = Column(Integer, default=0)
    target_port = Column(Integer, default=0)
    condition_json = Column(JSON, default={})

    workflow = relationship("Workflow", back_populates="edges")
