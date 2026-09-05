from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from backend.app.database import Base

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    project_name = Column(String, nullable=False)
    previous_commit = Column(String, default="none")
    new_commit = Column(String, default="head")
    branch = Column(String, default="main")
    
    # Rollback tracking fields
    is_rollback = Column(Boolean, default=False)
    target_rollback_commit = Column(String, nullable=True)
    build_state = Column(String, default="passed")      # passed, failed, skipped
    service_state = Column(String, default="active")     # active, stopped, error

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="running") # running, success, failed, rollback
    log = Column(Text, default="")
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Legacy fallback field compatibility
    commit_hash = Column(String, default="head")
    commit_message = Column(String, nullable=True)
