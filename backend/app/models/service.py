from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from backend.app.database import Base

class ServiceModel(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    systemd_name = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    project_name = Column(String, nullable=True)
    type = Column(String, default="daemon") # web, database, daemon, cache
    status = Column(String, default="running") # running, stopped, degraded, error
    enabled = Column(Boolean, default=True)
    port = Column(Integer, nullable=True)
    pid = Column(Integer, nullable=True)
    memory_mb = Column(Float, default=0.0)
    cpu_percent = Column(Float, default=0.0)
    uptime_seconds = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
