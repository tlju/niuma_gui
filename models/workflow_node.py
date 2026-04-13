from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from models.base import Base


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    node_key = Column(String(36), nullable=False, unique=True)
    node_type = Column(String(50), nullable=False)
    node_name = Column(String(100), nullable=False)
    pos_x = Column(Float, default=0)
    pos_y = Column(Float, default=0)
    config_json = Column(JSON, default={})

    workflow = relationship("Workflow", back_populates="nodes")
